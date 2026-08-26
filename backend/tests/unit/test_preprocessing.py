"""Tests unitaires — preprocessing image"""

import io

import httpx
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


def _mask_png_bytes(size=(300, 300), fill: int = 255) -> bytes:
    arr = np.full(size, fill, dtype=np.uint8)
    img = Image.fromarray(arr, mode="L")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _fake_segmentation_client(mask_png: bytes, status_code: int = 200) -> httpx.Client:
    """Client httpx dont le transport est mocké : simule le segmentation-service
    sans requête réseau réelle."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, content=mask_png)

    return httpx.Client(transport=httpx.MockTransport(handler))


# ── Shape & dtype (masking désactivé : pas d'appel réseau) ─────────────────────────────


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


# ── Masking via le segmentation-service (transport HTTP mocké) ─────────────────────────


def test_predict_lung_mask_calls_segmentation_service():
    mask_png = _mask_png_bytes(size=(300, 300), fill=255)
    client = _fake_segmentation_client(mask_png)

    mask = predict_lung_mask(
        make_test_image(size=(300, 300)), "http://segmentation-service:8001", timeout=5.0, client=client
    )

    assert mask.shape == (300, 300)
    assert mask.dtype == np.uint8


def test_predict_lung_mask_raises_on_http_error():
    client = _fake_segmentation_client(b"", status_code=503)

    with pytest.raises(httpx.HTTPStatusError):
        predict_lung_mask(make_test_image(), "http://segmentation-service:8001", timeout=5.0, client=client)


def test_preprocess_with_masking_calls_segmentation_service():
    mask_png = _mask_png_bytes(size=(300, 300), fill=255)
    client = _fake_segmentation_client(mask_png)

    result = preprocess_image(
        make_test_image(size=(300, 300)), img_size=(256, 256),
        masking=True, cropping=True,
        segmentation_service_url="http://segmentation-service:8001",
        segmentation_client=client,
    )
    assert result.shape == (1, 256, 256, 1)
