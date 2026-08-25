"""Tests ModelLoader — chargement modèle et inférence (coverage backend)."""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from app.models.loader import ModelLoader


def test_load_missing_file_leaves_not_loaded(tmp_path):
    loader = ModelLoader()

    loader.load(model_path=str(tmp_path / "missing.keras"))

    assert loader.is_loaded is False


def test_load_success_sets_is_loaded(tmp_path, monkeypatch):
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


def test_load_failure_keeps_not_loaded(tmp_path, monkeypatch):
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
