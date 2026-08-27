"""Tests métriques Prometheus — endpoint /metrics (US-18)."""

import io
import re

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from app.config import settings
from app.main import app
from app.models.loader import model_loader

client = TestClient(app)

FAKE_IMAGE = ("test.png", b"\x89PNG-fake-bytes", "image/png")

EXPECTED_METRICS = [
    "ds_covid_uptime_seconds",
    "ds_covid_model_loaded",
    "ds_covid_predictions_total",
    "ds_covid_http_requests_total",
    "ds_covid_inference_latency_seconds",
    "ds_covid_auth_failures_total",
    "ds_covid_low_confidence_predictions_total",
    "ds_covid_predictions_by_class_total",
]


def _real_png_bytes() -> bytes:
    img = Image.new("RGB", (32, 32), color=(120, 120, 120))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _metric_value(body: str, metric_with_labels: str) -> float:
    """Extrait la valeur courante d'une métrique (avec ou sans labels) depuis /metrics."""
    match = re.search(re.escape(metric_with_labels) + r" ([0-9.e+-]+)", body)
    return float(match.group(1)) if match else 0.0


# ── Présence des 8 métriques attendues par alert_rules.yml / le dashboard ──────

def test_metrics_returns_200():
    assert client.get("/metrics").status_code == 200


def test_metrics_content_type_is_prometheus_text():
    response = client.get("/metrics")
    assert response.headers["content-type"].startswith("text/plain")


def test_metrics_exposes_all_expected_metric_names():
    body = client.get("/metrics").text
    for metric in EXPECTED_METRICS:
        assert metric in body, f"{metric} absent de /metrics"


def test_metrics_declares_help_and_type_for_each_metric():
    body = client.get("/metrics").text
    for metric in EXPECTED_METRICS:
        assert f"# HELP {metric}" in body
        assert f"# TYPE {metric}" in body


# ── Comportement (avant/après, pas de valeur absolue — cf. CHANTIER_US18.md) ───

def test_http_requests_total_incremented_after_a_request():
    before = _metric_value(
        client.get("/metrics").text,
        'ds_covid_http_requests_total{path="/health",status="200"}',
    )
    client.get("/health")
    after = _metric_value(
        client.get("/metrics").text,
        'ds_covid_http_requests_total{path="/health",status="200"}',
    )
    assert after == before + 1


def test_auth_failure_increments_auth_failures_total(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret123")
    before = _metric_value(client.get("/metrics").text, "ds_covid_auth_failures_total")
    client.post(
        "/api/v1/predict",
        files={"file": FAKE_IMAGE},
        headers={"X-API-Key": "wrong"},
    )
    after = _metric_value(client.get("/metrics").text, "ds_covid_auth_failures_total")
    assert after == before + 1


def test_predict_success_increments_class_and_latency_metrics(monkeypatch):
    monkeypatch.setattr(model_loader, "is_loaded", True)
    monkeypatch.setattr(
        model_loader, "predict", lambda img_array: np.array([0.7, 0.1, 0.1, 0.1])
    )
    monkeypatch.setattr(settings, "masking", False)
    label = f'ds_covid_predictions_by_class_total{{predicted_class="{settings.class_names[0]}"}}'

    before_class = _metric_value(client.get("/metrics").text, label)
    before_bucket_count = _metric_value(
        client.get("/metrics").text, "ds_covid_inference_latency_seconds_count"
    )

    client.post(
        "/api/v1/predict",
        files={"file": ("test.png", _real_png_bytes(), "image/png")},
    )

    body_after = client.get("/metrics").text
    assert _metric_value(body_after, label) == before_class + 1
    assert (
        _metric_value(body_after, "ds_covid_inference_latency_seconds_count")
        == before_bucket_count + 1
    )


def test_predict_low_confidence_increments_low_confidence_total(monkeypatch):
    monkeypatch.setattr(model_loader, "is_loaded", True)
    monkeypatch.setattr(
        model_loader, "predict", lambda img_array: np.array([0.4, 0.3, 0.2, 0.1])
    )
    monkeypatch.setattr(settings, "masking", False)

    before = _metric_value(
        client.get("/metrics").text, "ds_covid_low_confidence_predictions_total"
    )
    client.post(
        "/api/v1/predict",
        files={"file": ("test.png", _real_png_bytes(), "image/png")},
    )
    after = _metric_value(
        client.get("/metrics").text, "ds_covid_low_confidence_predictions_total"
    )
    assert after == before + 1
