"""Tests unitaires — preprocessing image"""

import io

import numpy as np
import pytest
from PIL import Image

from app.features.preprocessing import predict_lung_mask, preprocess_image


def make_test_image(size=(300, 300), mode="L") -> bytes:
    """Crée une image PNG en mémoire pour les tests."""
    if mode == "RGB":
        arr = np.random.randint(0, 255, (*size, 3), dtype=np.uint8)
    elif mode == "RGBA":
        arr = np.random.randint(0, 255, (*size, 4), dtype=np.uint8)
    else:
        arr = np.random.randint(0, 255, size, dtype=np.uint8)
    img = Image.fromarray(arr, mode=mode)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class FakeSegmentationModel:
    """Simule `ModelLoader.predict` (renvoie directement un mask sans dim de batch),
    sans dépendre d'un vrai modèle Keras entraîné."""

    def __init__(self, img_size: int, fill: float = 1.0):
        self.img_size = img_size
        self.fill = fill

    def predict(self, img_array: np.ndarray) -> np.ndarray:
        assert img_array.shape == (1, self.img_size, self.img_size, 1)
        return np.full((self.img_size, self.img_size, 1), self.fill, dtype=np.float32)


# ── Shape & dtype (masking désactivé : pas de dépendance à un modèle de segmentation) ──


def test_preprocess_output_shape():
    result = preprocess_image(make_test_image(), img_size=(256, 256), masking=False)
    assert result.shape == (1, 256, 256, 1)


def test_preprocess_dtype():
    result = preprocess_image(make_test_image(), masking=False)
    assert result.dtype == np.float32


def test_preprocess_custom_size():
    result = preprocess_image(make_test_image(), img_size=(128, 128), masking=False)
    assert result.shape == (1, 128, 128, 1)


def test_preprocess_batch_dim():
    """La dimension batch doit toujours être 1."""
    result = preprocess_image(make_test_image(), masking=False)
    assert result.ndim == 4
    assert result.shape[0] == 1


# ── Normalisation : [-1, 1] (identique à l'entraînement, cf. scripts/preprocess.py) ────


def test_preprocess_normalized():
    result = preprocess_image(make_test_image(), masking=False)
    assert result.min() >= -1.0
    assert result.max() <= 1.0


def test_preprocess_not_constant():
    result = preprocess_image(make_test_image(), masking=False)
    assert result.min() != result.max()


# ── Conversion de mode : toute image est ramenée en niveaux de gris (1 canal) ──────────


def test_preprocess_rgb_converted_to_grayscale():
    result = preprocess_image(make_test_image(mode="RGB"), masking=False)
    assert result.shape == (1, 256, 256, 1)


def test_preprocess_rgba_converted_to_grayscale():
    result = preprocess_image(make_test_image(mode="RGBA"), masking=False)
    assert result.shape == (1, 256, 256, 1)


# ── Resize ───────────────────────────────────────────────────────────────────────────


def test_preprocess_small_image_upscaled():
    result = preprocess_image(make_test_image(size=(32, 32)), masking=False)
    assert result.shape == (1, 256, 256, 1)


def test_preprocess_large_image_downscaled():
    result = preprocess_image(make_test_image(size=(1024, 1024)), masking=False)
    assert result.shape == (1, 256, 256, 1)


def test_preprocess_non_square_image():
    result = preprocess_image(make_test_image(size=(640, 480)), masking=False)
    assert result.shape == (1, 256, 256, 1)


# ── Robustesse ───────────────────────────────────────────────────────────────────────


def test_preprocess_invalid_bytes_raises():
    """Des bytes invalides doivent lever une exception."""
    with pytest.raises(ValueError):
        preprocess_image(b"not_an_image", masking=False)


def test_preprocess_masking_without_model_falls_back(caplog):
    """masking=True mais segmentation_model=None : ne doit pas planter, juste
    dégrader (image non masquée) en loggant un avertissement."""
    result = preprocess_image(make_test_image(), masking=True, segmentation_model=None)
    assert result.shape == (1, 256, 256, 1)
    assert "non masquée" in caplog.text


# ── Masking via un modèle de segmentation (mock) ────────────────────────────────────────


def test_predict_lung_mask_shape():
    img = np.random.randint(0, 255, (300, 300), dtype=np.uint8)
    model = FakeSegmentationModel(img_size=256, fill=1.0)  # prédit "tout est poumon"
    mask = predict_lung_mask(img, model, model_img_size=256, clean_components=2, clean_kernel=15)
    assert mask.shape == img.shape
    assert mask.dtype == np.uint8


def test_preprocess_with_masking_model():
    model = FakeSegmentationModel(img_size=256, fill=1.0)
    result = preprocess_image(
        make_test_image(size=(300, 300)), img_size=(256, 256),
        masking=True, cropping=True, segmentation_model=model,
    )
    assert result.shape == (1, 256, 256, 1)
