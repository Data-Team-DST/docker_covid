"""Tests unitaires — preprocessing image"""

import io

import numpy as np
import pytest
from PIL import Image

from app.features.preprocessing import preprocess_image


def make_test_image(size=(300, 300), mode="RGB") -> bytes:
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


# ── Shape & dtype ─────────────────────────────────────────────────────────────

def test_preprocess_output_shape():
    result = preprocess_image(make_test_image(), img_size=(224, 224))
    assert result.shape == (1, 224, 224, 3)


def test_preprocess_dtype():
    result = preprocess_image(make_test_image())
    assert result.dtype == np.float32


def test_preprocess_custom_size():
    result = preprocess_image(make_test_image(), img_size=(128, 128))
    assert result.shape == (1, 128, 128, 3)


def test_preprocess_batch_dim():
    """La dimension batch doit toujours être 1."""
    result = preprocess_image(make_test_image())
    assert result.ndim == 4
    assert result.shape[0] == 1


# ── Normalisation ─────────────────────────────────────────────────────────────

def test_preprocess_normalized():
    result = preprocess_image(make_test_image())
    assert result.min() >= 0.0
    assert result.max() <= 1.0


def test_preprocess_not_all_zero():
    result = preprocess_image(make_test_image())
    assert result.max() > 0.0


# ── Conversion de mode ────────────────────────────────────────────────────────

def test_preprocess_grayscale_converted():
    """Une image grayscale (L) doit être convertie en RGB → 3 canaux."""
    result = preprocess_image(make_test_image(mode="L"))
    assert result.shape == (1, 224, 224, 3)


def test_preprocess_rgba_converted():
    """Une image RGBA doit être convertie en RGB → 3 canaux."""
    result = preprocess_image(make_test_image(mode="RGBA"))
    assert result.shape == (1, 224, 224, 3)


# ── Resize ────────────────────────────────────────────────────────────────────

def test_preprocess_small_image_upscaled():
    result = preprocess_image(make_test_image(size=(32, 32)))
    assert result.shape == (1, 224, 224, 3)


def test_preprocess_large_image_downscaled():
    result = preprocess_image(make_test_image(size=(1024, 1024)))
    assert result.shape == (1, 224, 224, 3)


def test_preprocess_non_square_image():
    result = preprocess_image(make_test_image(size=(640, 480)))
    assert result.shape == (1, 224, 224, 3)


# ── Robustesse ────────────────────────────────────────────────────────────────

def test_preprocess_invalid_bytes_raises():
    """Des bytes invalides doivent lever une exception."""
    with pytest.raises(Exception):
        preprocess_image(b"not_an_image")
