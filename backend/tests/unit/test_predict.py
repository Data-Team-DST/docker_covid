"""Tests endpoint /predict — chemin succès et gestion d'erreur (coverage backend)."""

import io
import logging

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from app.config import settings
from app.logging_config import TELEMETRY_LOGGER_NAME
from app.main import app
from app.models.loader import model_loader

client = TestClient(app)


def _real_png_bytes() -> bytes:
    img = Image.new("RGB", (32, 32), color=(120, 120, 120))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_predict_success_returns_scores(monkeypatch):
    monkeypatch.setattr(model_loader, "is_loaded", True)
    monkeypatch.setattr(
        model_loader, "predict", lambda img_array: np.array([0.7, 0.1, 0.1, 0.1])
    )
    # Masking appelle le segmentation-service en HTTP : hors scope de ce test
    # (couvert par test_preprocessing.py), on le désactive ici.
    monkeypatch.setattr(settings, "masking", False)

    response = client.post(
        "/api/v1/predict",
        files={"file": ("test.png", _real_png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["predicted_class"] == settings.class_names[0]
    assert data["confidence"] == 0.7
    assert set(data["scores"]) == set(settings.class_names)
    assert data["latency_ms"] >= 0


def test_predict_success_logs_telemetry_with_scores(monkeypatch, caplog):
    """La télémétrie drift (US-20) doit recevoir les scores à chaque prédiction réussie."""
    monkeypatch.setattr(model_loader, "is_loaded", True)
    monkeypatch.setattr(
        model_loader, "predict", lambda img_array: np.array([0.7, 0.1, 0.1, 0.1])
    )
    monkeypatch.setattr(settings, "masking", False)

    with caplog.at_level(logging.INFO, logger=TELEMETRY_LOGGER_NAME):
        response = client.post(
            "/api/v1/predict",
            files={"file": ("test.png", _real_png_bytes(), "image/png")},
        )

    assert response.status_code == 200
    telemetry_records = [r for r in caplog.records if r.name == TELEMETRY_LOGGER_NAME]
    assert len(telemetry_records) == 1
    extra_data = telemetry_records[0].extra_data
    assert extra_data["predicted_class"] == settings.class_names[0]
    assert extra_data["confidence"] == 0.7
    assert set(extra_data["scores"]) == set(settings.class_names)


def test_predict_internal_error_returns_500(monkeypatch):
    monkeypatch.setattr(model_loader, "is_loaded", True)

    response = client.post(
        "/api/v1/predict",
        files={"file": ("test.png", b"\x89PNG-not-a-real-image", "image/png")},
    )

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert detail == "Erreur interne lors de la prédiction"
    assert "PNG" not in detail  # le détail de l'exception PIL ne doit pas fuiter au client
