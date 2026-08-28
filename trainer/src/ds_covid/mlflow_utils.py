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
import tempfile
from pathlib import Path

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

    def _configure_remote(self):
        tracking_uri = os.getenv("DAGSHUB_MLFLOW_TRACKING_URI")
        username = os.getenv("DAGSHUB_USERNAME")
        token = os.getenv("DAGSHUB_TOKEN")
        if not token or token.startswith("${"):
            token = os.getenv("REMOTE_S3_ACCESS_KEY")
        if not all((tracking_uri, username, token)):
            return

        try:
            os.environ["MLFLOW_TRACKING_URI"] = tracking_uri
            os.environ["MLFLOW_REGISTRY_URI"] = tracking_uri
            os.environ["MLFLOW_TRACKING_USERNAME"] = username
            os.environ["MLFLOW_TRACKING_PASSWORD"] = token
            self.remote_client = MlflowClient(
                tracking_uri=tracking_uri,
                registry_uri=tracking_uri,
            )
            experiment = self.remote_client.get_experiment_by_name(self.experiment_name)
            if experiment is None:
                experiment_id = self.remote_client.create_experiment(self.experiment_name)
            else:
                experiment_id = experiment.experiment_id
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

    def _remote_call(self, operation, *args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except Exception as error:
            print(f"[WARN] Écriture DagsHub MLflow ignorée : {error}", flush=True)
            self.remote_client = None
            self.remote_run_id = None
            return None


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
