"""Tests unitaires du double tracking MLflow local et DagsHub."""
import os
from unittest.mock import Mock

from ds_covid.mlflow_utils import DualMlflowRun


def test_configure_remote_restores_mlflow_environment(monkeypatch):
    """L'initialisation DagsHub ne doit pas modifier l'environnement local."""
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://local-mlflow:5000")
    monkeypatch.setenv("MLFLOW_REGISTRY_URI", "http://local-mlflow:5000")
    monkeypatch.setenv("MLFLOW_TRACKING_USERNAME", "local-user")
    monkeypatch.setenv("MLFLOW_TRACKING_PASSWORD", "local-password")
    monkeypatch.setenv("DAGSHUB_MLFLOW_TRACKING_URI", "https://dagshub.example/mlflow")
    monkeypatch.setenv("DAGSHUB_USERNAME", "dagshub-user")
    monkeypatch.setenv("DAGSHUB_TOKEN", "dagshub-token")

    remote_client = Mock()
    remote_client.get_experiment_by_name.return_value = Mock(experiment_id="1")
    monkeypatch.setattr("ds_covid.mlflow_utils.MlflowClient", lambda **_: remote_client)

    DualMlflowRun("experiment")._configure_remote()

    assert os.environ["MLFLOW_TRACKING_URI"] == "http://local-mlflow:5000"
    assert os.environ["MLFLOW_REGISTRY_URI"] == "http://local-mlflow:5000"
    assert os.environ["MLFLOW_TRACKING_USERNAME"] == "local-user"
    assert os.environ["MLFLOW_TRACKING_PASSWORD"] == "local-password"


def test_log_remote_metrics_uses_dagshub_credentials_only_during_call(monkeypatch):
    """Chaque métrique distante reçoit les credentials DagsHub et le bon step."""
    mirror = DualMlflowRun("experiment")
    mirror.remote_client = Mock()
    mirror.remote_run_id = "remote-run"
    mirror._remote_environment = {
        "MLFLOW_TRACKING_USERNAME": "dagshub-user",
        "MLFLOW_TRACKING_PASSWORD": "dagshub-token",
    }
    monkeypatch.delenv("MLFLOW_TRACKING_USERNAME", raising=False)
    monkeypatch.delenv("MLFLOW_TRACKING_PASSWORD", raising=False)

    credentials_seen = []

    def log_metric(*args, **kwargs):
        credentials_seen.append(
            (
                os.environ["MLFLOW_TRACKING_USERNAME"],
                os.environ["MLFLOW_TRACKING_PASSWORD"],
                args,
                kwargs,
            )
        )

    mirror.remote_client.log_metric.side_effect = log_metric

    mirror.log_remote_metrics({"val_loss": 0.25}, step=4)

    assert credentials_seen == [
        (
            "dagshub-user",
            "dagshub-token",
            ("remote-run", "val_loss", 0.25),
            {"step": 4},
        )
    ]
    assert "MLFLOW_TRACKING_USERNAME" not in os.environ
    assert "MLFLOW_TRACKING_PASSWORD" not in os.environ