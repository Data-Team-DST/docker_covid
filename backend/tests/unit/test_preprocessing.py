"""Tests unitaires — preprocessing image"""
import io
import numpy as np
import pytest
from PIL import Image

from app.features.preprocessing import preprocess_image


def make_test_image(size=(300, 300), mode="RGB") -> bytes:
    """Crée une image PNG en mémoire pour les tests."""
    img = Image.fromarray(
        np.random.randint(0, 255, (*size, 3), dtype=np.uint8) if mode == "RGB"
        else np.random.randint(0, 255, size, dtype=np.uint8)
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_preprocess_output_shape():
    img_bytes = make_test_image()
    result = preprocess_image(img_bytes, img_size=(224, 224))
    assert result.shape == (1, 224, 224, 3)


def test_preprocess_normalized():
    img_bytes = make_test_image()
    result = preprocess_image(img_bytes)
    assert result.min() >= 0.0
    assert result.max() <= 1.0


def test_preprocess_dtype():
    img_bytes = make_test_image()
    result = preprocess_image(img_bytes)
    assert result.dtype == np.float32


def test_preprocess_grayscale_converted():
    """Une image en niveaux de gris doit être convertie en RGB."""
    img = Image.fromarray(np.random.randint(0, 255, (224, 224), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result = preprocess_image(buf.getvalue())
    assert result.shape == (1, 224, 224, 3)


def test_preprocess_custom_size():
    img_bytes = make_test_image()
    result = preprocess_image(img_bytes, img_size=(128, 128))
    assert result.shape == (1, 128, 128, 3)
