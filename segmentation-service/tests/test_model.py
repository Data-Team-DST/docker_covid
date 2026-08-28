import io
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest
from PIL import Image

from segmentation_service.model import (
    ModelLoader,
    clean_mask,
    model_loader,
    predict_lung_mask,
)


def make_png_bytes(size=(300, 300)) -> bytes:
    arr = np.random.randint(0, 255, size, dtype=np.uint8)
    img = Image.fromarray(arr, mode="L")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── clean_mask ───────────────────────────────────────────────────────────────


def test_clean_mask_shape_and_dtype():
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[10:30, 10:30] = 255
    cleaned = clean_mask(mask, n_components=2, closing_kernel_size=5)
    assert cleaned.shape == mask.shape
    assert cleaned.dtype == np.uint8


def test_clean_mask_removes_small_islands():
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[10:30, 10:30] = 255  # grande composante
    mask[50, 50] = 255  # îlot isolé (1 pixel)
    cleaned = clean_mask(mask, n_components=1, closing_kernel_size=3)
    assert cleaned[50, 50] == 0
    assert cleaned[20, 20] == 255


def test_clean_mask_empty_mask_returns_empty():
    mask = np.zeros((32, 32), dtype=np.uint8)
    cleaned = clean_mask(mask)
    assert cleaned.max() == 0


# ── predict_lung_mask ──────────────────────────────────────────────────────────


class _FakeModel:
    def predict(self, x, verbose=0):
        batch, h, w, _ = x.shape
        return np.ones((batch, h, w, 1), dtype=np.float32)


def test_predict_lung_mask_shape(monkeypatch):
    monkeypatch.setattr(model_loader, "is_loaded", True)
    monkeypatch.setattr(model_loader, "_model", _FakeModel())

    png = predict_lung_mask(make_png_bytes(size=(300, 200)), img_size=256, clean_components=2, clean_kernel=5)

    img = Image.open(io.BytesIO(png))
    assert img.size == (200, 300)  # PIL: (width, height)


def test_predict_lung_mask_invalid_bytes_raises():
    with pytest.raises(ValueError):
        predict_lung_mask(b"not-an-image", img_size=256, clean_components=2, clean_kernel=5)


def test_predict_lung_mask_without_model_raises():
    model_loader.is_loaded = False
    with pytest.raises(RuntimeError, match="non chargé"):
        predict_lung_mask(make_png_bytes(), img_size=256, clean_components=2, clean_kernel=5)


# ── ModelLoader.load ─────────────────────────────────────────────────────────


def test_load_missing_file_leaves_not_loaded(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "segmentation_service.config.settings.mlflow_tracking_uri", ""
    )
    loader = ModelLoader()
    loader.load(model_path=str(tmp_path / "missing.keras"))
    assert loader.is_loaded is False


def test_load_success_sets_is_loaded(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "segmentation_service.config.settings.mlflow_tracking_uri", ""
    )
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
    monkeypatch.setattr(
        "segmentation_service.config.settings.mlflow_tracking_uri", ""
    )
    model_path = tmp_path / "model.keras"
    model_path.write_bytes(b"fake-keras-model")

    def _raise(*args, **kwargs):
        raise ValueError("modèle corrompu")

    fake_tf = SimpleNamespace(keras=SimpleNamespace(models=SimpleNamespace(load_model=_raise)))
    monkeypatch.setitem(sys.modules, "tensorflow", fake_tf)

    loader = ModelLoader()
    loader.load(model_path=str(model_path))

    assert loader.is_loaded is False


def test_load_from_registry_success(monkeypatch):
    monkeypatch.setattr(
        "segmentation_service.config.settings.mlflow_tracking_uri",
        "http://mlflow:5000",
    )
    monkeypatch.setattr(
        "segmentation_service.config.settings.mlflow_model_name", "segmentation"
    )
    monkeypatch.setattr(
        "segmentation_service.config.settings.mlflow_model_stage", "Production"
    )

    fake_model = MagicMock()
    fake_mlflow = SimpleNamespace(
        set_tracking_uri=MagicMock(),
        keras=SimpleNamespace(load_model=MagicMock(return_value=fake_model)),
    )
    monkeypatch.setitem(sys.modules, "mlflow", fake_mlflow)

    loader = ModelLoader()
    loader.load(model_path="unused")

    assert loader.is_loaded is True
    assert loader.source == "registry"
    fake_mlflow.keras.load_model.assert_called_once_with(
        "models:/segmentation/Production", load_model_kwargs={"compile": False}
    )


def test_load_falls_back_to_local_when_registry_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "segmentation_service.config.settings.mlflow_tracking_uri",
        "http://mlflow:5000",
    )
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
