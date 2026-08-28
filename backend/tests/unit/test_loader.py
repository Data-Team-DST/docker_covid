"""Tests ModelLoader — chargement modèle et inférence (coverage backend)."""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from app.models.loader import ModelLoader


def test_load_missing_file_leaves_not_loaded(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.mlflow_tracking_uri", "")
    loader = ModelLoader()

    loader.load(model_path=str(tmp_path / "missing.keras"))

    assert loader.is_loaded is False


def test_load_success_sets_is_loaded(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.mlflow_tracking_uri", "")
    model_path = tmp_path / "model.keras"
    model_path.write_bytes(b"fake-keras-model")

    fake_model = MagicMock()
    fake_tf = SimpleNamespace(
        keras=SimpleNamespace(
            models=SimpleNamespace(load_model=MagicMock(return_value=fake_model))
        )
    )
    monkeypatch.setitem(sys.modules, "tensorflow", fake_tf)

    loader = ModelLoader()
    loader.load(model_path=str(model_path))

    assert loader.is_loaded is True
    assert loader.source == "local"


def test_load_failure_keeps_not_loaded(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.mlflow_tracking_uri", "")
    model_path = tmp_path / "model.keras"
    model_path.write_bytes(b"fake-keras-model")

    def _raise(*args, **kwargs):
        raise ValueError("modèle corrompu")

    fake_tf = SimpleNamespace(
        keras=SimpleNamespace(models=SimpleNamespace(load_model=_raise))
    )
    monkeypatch.setitem(sys.modules, "tensorflow", fake_tf)

    loader = ModelLoader()
    loader.load(model_path=str(model_path))

    assert loader.is_loaded is False


def test_load_from_registry_success(monkeypatch):
    monkeypatch.setattr("app.config.settings.mlflow_tracking_uri", "http://mlflow:5000")
    monkeypatch.setattr("app.config.settings.mlflow_model_name", "classification")
    monkeypatch.setattr("app.config.settings.mlflow_model_stage", "Production")

    fake_model = MagicMock()
    fake_mlflow = SimpleNamespace(
        set_tracking_uri=MagicMock(),
        keras=SimpleNamespace(load_model=MagicMock(return_value=fake_model)),
    )
    monkeypatch.setitem(sys.modules, "mlflow", fake_mlflow)

    loader = ModelLoader()
    loader.load()

    assert loader.is_loaded is True
    assert loader.source == "registry"
    fake_mlflow.keras.load_model.assert_called_once_with(
        "models:/classification/Production"
    )


def test_load_falls_back_to_local_when_registry_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.mlflow_tracking_uri", "http://mlflow:5000")
    model_path = tmp_path / "model.keras"
    model_path.write_bytes(b"fake-keras-model")

    def _raise(*args, **kwargs):
        raise ConnectionError("MLflow injoignable")

    fake_mlflow = SimpleNamespace(set_tracking_uri=_raise)
    monkeypatch.setitem(sys.modules, "mlflow", fake_mlflow)

    fake_model = MagicMock()
    fake_tf = SimpleNamespace(
        keras=SimpleNamespace(
            models=SimpleNamespace(load_model=MagicMock(return_value=fake_model))
        )
    )
    monkeypatch.setitem(sys.modules, "tensorflow", fake_tf)

    loader = ModelLoader()
    loader.load(model_path=str(model_path))

    assert loader.is_loaded is True
    assert loader.source == "local"


def test_load_no_source_available_leaves_not_loaded(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.mlflow_tracking_uri", "http://mlflow:5000")

    def _raise(*args, **kwargs):
        raise ConnectionError("MLflow injoignable")

    fake_mlflow = SimpleNamespace(set_tracking_uri=_raise)
    monkeypatch.setitem(sys.modules, "mlflow", fake_mlflow)

    loader = ModelLoader()
    loader.load(model_path=str(tmp_path / "missing.keras"))

    assert loader.is_loaded is False
    assert loader.source is None


def test_predict_raises_when_not_loaded():
    loader = ModelLoader()

    with pytest.raises(RuntimeError, match="non chargé"):
        loader.predict(np.zeros((1, 224, 224, 3)))


def test_predict_returns_first_row():
    loader = ModelLoader()
    loader.is_loaded = True
    loader._model = MagicMock()
    loader._model.predict.return_value = np.array([[0.1, 0.2, 0.6, 0.1]])

    result = loader.predict(np.zeros((1, 224, 224, 3)))

    assert result.tolist() == [0.1, 0.2, 0.6, 0.1]
