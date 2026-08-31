"""Callback Keras pour logger les métriques dans MLflow au fil de l'entraînement.

mlflow.keras.autolog() a été évalué et écarté : sur un entraînement en plusieurs
phases avec des model.fit() successifs dans le même run (cf. train_segmentation.py,
phase freeze puis fine-tune), il tente de relogger le paramètre "epochs" avec une
valeur différente à la 2e phase, ce que MLflow interdit (MlflowException avalée en
warning) — la 2e phase se retrouve alors silencieusement non trackée. Ce callback,
plus simple, ne logue que les métriques (jamais les paramètres) donc n'a pas ce
problème, et permet un décalage de step explicite pour enchaîner plusieurs phases
sur une timeline continue.
"""

import os
import platform
import tempfile
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from typing import Iterator

import mlflow
from mlflow.tracking import MlflowClient
import tensorflow as tf


class DualMlflowRun:
    """Keep the local MLflow run and optionally mirror it to DagsHub."""

    def __init__(self, experiment_name: str, run_name: str | None = None):
        self.experiment_name = experiment_name
        self.run_name = run_name
        self.remote_client = None
        self.remote_run_id = None
        self._remote_environment: dict[str, str] = {}

    def __enter__(self):
        self.local_run = mlflow.start_run(run_name=self.run_name)
        self._configure_remote()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.remote_client and self.remote_run_id:
            self._remote_call(self.remote_client.set_terminated,
                self.remote_run_id,
                status="FAILED" if exc_type else "FINISHED",
            )
        mlflow.end_run(status="FAILED" if exc_type else "FINISHED")
        return False

    @contextmanager
    def _remote_credentials(self) -> Iterator[None]:
        """Expose temporairement les credentials requis par le client DagsHub."""
        previous_environment = {
            key: os.environ.get(key) for key in self._remote_environment
        }
        try:
            os.environ.update(self._remote_environment)
            yield
        finally:
            for key, value in previous_environment.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def _configure_remote(self):
        tracking_uri = os.getenv("DAGSHUB_MLFLOW_TRACKING_URI")
        username = os.getenv("DAGSHUB_USERNAME")
        token = os.getenv("DAGSHUB_TOKEN")
        if not token or token.startswith("${"):
            token = os.getenv("REMOTE_S3_ACCESS_KEY")
        if not all((tracking_uri, username, token)):
            return

        self._remote_environment = {
            "MLFLOW_TRACKING_URI": tracking_uri,
            "MLFLOW_REGISTRY_URI": tracking_uri,
            "MLFLOW_TRACKING_USERNAME": username,
            "MLFLOW_TRACKING_PASSWORD": token,
        }
        try:
            with self._remote_credentials():
                self.remote_client = MlflowClient(
                    tracking_uri=tracking_uri,
                    registry_uri=tracking_uri,
                )
                experiment = self.remote_client.get_experiment_by_name(
                    self.experiment_name
                )
                experiment_id = (
                    self.remote_client.create_experiment(self.experiment_name)
                    if experiment is None
                    else experiment.experiment_id
                )
                self.remote_run_id = self.remote_client.create_run(
                    experiment_id=experiment_id,
                    tags={"mlflow.runName": self.run_name} if self.run_name else None,
                ).info.run_id
        except Exception as error:  # Remote tracking must not stop local training.
            print(f"[WARN] DagsHub MLflow indisponible : {error}", flush=True)
            self.remote_client = None
            self.remote_run_id = None

    def log_params(self, params: dict):
        mlflow.log_params(params)
        if self.remote_client and self.remote_run_id:
            for key, value in params.items():
                self._remote_call(
                    self.remote_client.log_param, self.remote_run_id, key, str(value)
                )

    def log_tags(self, tags: dict):
        """Enregistre les tags de reproductibilité dans les deux trackers."""
        normalized_tags = {key: str(value) for key, value in tags.items()}
        mlflow.set_tags(normalized_tags)
        for key, value in normalized_tags.items():
            if not self.remote_client or not self.remote_run_id:
                return
            self._remote_call(
                self.remote_client.set_tag, self.remote_run_id, key, value
            )

    def log_config_artifact(self, config_path: Path):
        """Enregistre le fichier de configuration dans les deux trackers."""
        if not config_path.is_file():
            return
        mlflow.log_artifact(str(config_path), artifact_path="config")
        if not self.remote_client or not self.remote_run_id:
            return
        self._remote_call(
            self.remote_client.log_artifact,
            self.remote_run_id,
            str(config_path),
            "config",
        )

    def log_metrics(self, metrics: dict, step: int = 0):
        mlflow.log_metrics(metrics, step=step)
        self.log_remote_metrics(metrics, step)

    def log_remote_metrics(self, metrics: dict, step: int = 0):
        if self.remote_client and self.remote_run_id:
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    self._remote_call(
                        self.remote_client.log_metric,
                        self.remote_run_id,
                        key,
                        float(value),
                        step=step,
                    )

    def log_model(self, model, artifact_path: str):
        if self.remote_client and self.remote_run_id:
            with tempfile.TemporaryDirectory() as temp_dir:
                model_dir = Path(temp_dir) / "model"
                mlflow.keras.save_model(model, str(model_dir))
                self._remote_call(
                    self.remote_client.log_artifacts,
                    self.remote_run_id,
                    str(model_dir),
                    artifact_path,
                )

    def register_model(self, model_name: str, artifact_path: str = "model"):
        """Crée une version DagsHub du modèle miroir lorsqu'il est disponible."""
        if not self.remote_client or not self.remote_run_id:
            return None
        try:
            with self._remote_credentials():
                try:
                    self.remote_client.get_registered_model(model_name)
                except Exception:  # noqa: BLE001
                    self.remote_client.create_registered_model(model_name)
                return self.remote_client.create_model_version(
                    name=model_name,
                    source=f"runs:/{self.remote_run_id}/{artifact_path}",
                    run_id=self.remote_run_id,
                )
        except Exception as error:  # noqa: BLE001
            print(f"[WARN] Enregistrement du modèle DagsHub ignoré : {error}", flush=True)
            return None

    def _remote_call(self, operation, *args, **kwargs):
        if not self.remote_client or not self.remote_run_id:
            return None
        try:
            with self._remote_credentials():
                return operation(*args, **kwargs)
        except Exception as error:  # noqa: BLE001
            print(f"[WARN] Écriture DagsHub MLflow ignorée : {error}", flush=True)
            self.remote_client = None
            self.remote_run_id = None
            return None


def collect_run_tags(config_path: Path, params: dict, model_name: str) -> dict:
    """Construit les tags de reproductibilité communs aux entraînements."""
    return {
        "config.file": config_path.name,
        "config.sha256": sha256(config_path.read_bytes()).hexdigest(),
        "config.img_size": params["preprocess"]["img_size"],
        "config.random_seed": params["preprocess"]["random_seed"],
        "mlflow.model_name": model_name,
        "runtime.python_version": platform.python_version(),
        "runtime.tensorflow_version": tf.__version__,
        "runtime.gpu_count": len(tf.config.list_physical_devices("GPU")),
    }


class MlflowEpochLogger(tf.keras.callbacks.Callback):
    """Logue les métriques de chaque epoch dans MLflow (loss, val_loss, etc.),
    au lieu d'un seul résumé après la fin de l'entraînement — permet de suivre
    la progression en temps réel dans l'UI MLflow pendant que le run tourne.
    """

    def __init__(self, step_offset: int = 0, mirror: DualMlflowRun | None = None):
        super().__init__()
        self.step_offset = step_offset
        self.mirror = mirror

    def on_epoch_end(self, epoch, logs=None):
        """Logue les métriques Keras de l'epoch courante au step step_offset + epoch."""
        if logs:
            step = self.step_offset + epoch
            mlflow.log_metrics(logs, step=step)
            if self.mirror:
                self.mirror.log_remote_metrics(logs, step=step)
