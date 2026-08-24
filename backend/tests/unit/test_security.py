"""Tests sécurité — clé API, rate limiting, validation stricte /predict (US-12)."""

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models.loader import model_loader

client = TestClient(app)

FAKE_IMAGE = ("test.png", b"\x89PNG-fake-bytes", "image/png")


# ── Clé API ──────────────────────────────────────────────────────────────────

def test_predict_no_key_when_configured_returns_401(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret123")
    response = client.post("/api/v1/predict", files={"file": FAKE_IMAGE})
    assert response.status_code == 401


def test_predict_wrong_key_returns_401(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret123")
    response = client.post(
        "/api/v1/predict",
        files={"file": FAKE_IMAGE},
        headers={"X-API-Key": "wrong"},
    )
    assert response.status_code == 401


def test_predict_correct_key_not_blocked(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret123")
    response = client.post(
        "/api/v1/predict",
        files={"file": FAKE_IMAGE},
        headers={"X-API-Key": "secret123"},
    )
    assert response.status_code != 401


def test_health_stays_public_when_key_configured(monkeypatch):
    """/health n'est jamais protégé — requis par le healthcheck Docker/CI sans clé."""
    monkeypatch.setattr(settings, "api_key", "secret123")
    assert client.get("/health").status_code == 200


def test_metrics_stays_public_when_key_configured(monkeypatch):
    """/metrics n'est jamais protégé — requis par le scraping Prometheus sans clé."""
    monkeypatch.setattr(settings, "api_key", "secret123")
    assert client.get("/metrics").status_code == 200


# ── Validation stricte ───────────────────────────────────────────────────────

def test_predict_rejects_bad_content_type(monkeypatch):
    monkeypatch.setattr(model_loader, "is_loaded", True)
    response = client.post(
        "/api/v1/predict",
        files={"file": ("test.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400


def test_predict_rejects_oversized_file(monkeypatch):
    monkeypatch.setattr(model_loader, "is_loaded", True)
    monkeypatch.setattr(settings, "max_upload_size_mb", 0)
    response = client.post("/api/v1/predict", files={"file": FAKE_IMAGE})
    assert response.status_code == 400
    assert "volumineux" in response.json()["detail"]


# ── Rate limiting ────────────────────────────────────────────────────────────

def test_predict_rate_limit_eventually_returns_429():
    max_attempts = settings.rate_limit_per_minute + 20
    statuses = []
    for _ in range(max_attempts):
        response = client.post("/api/v1/predict", files={"file": FAKE_IMAGE})
        statuses.append(response.status_code)
        if response.status_code == 429:
            break
    assert 429 in statuses
