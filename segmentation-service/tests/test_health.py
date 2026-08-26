import io

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from segmentation_service.main import app
from segmentation_service.model import model_loader

client = TestClient(app)


def make_png_bytes(size=(64, 64)) -> bytes:
    arr = np.random.randint(0, 255, size, dtype=np.uint8)
    img = Image.fromarray(arr, mode="L")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert body["service"] == "segmentation-service"
    assert "model_loaded" in body


def test_health_reports_model_loaded(monkeypatch):
    monkeypatch.setattr(model_loader, "is_loaded", True)
    r = client.get("/health")
    assert r.json()["model_loaded"] is True


def test_segment_without_model_returns_503():
    r = client.post(
        "/v1/segment",
        files={"file": ("test.png", b"not-a-real-image", "image/png")},
    )
    assert r.status_code == 503


def test_segment_invalid_image_returns_400(monkeypatch):
    monkeypatch.setattr(model_loader, "is_loaded", True)
    r = client.post(
        "/v1/segment",
        files={"file": ("test.png", b"not-a-real-image", "image/png")},
    )
    assert r.status_code == 400


class _FakeModel:
    def predict(self, x, verbose=0):
        batch, h, w, _ = x.shape
        return np.ones((batch, h, w, 1), dtype=np.float32)


def test_segment_success_returns_png(monkeypatch):
    monkeypatch.setattr(model_loader, "is_loaded", True)
    monkeypatch.setattr(model_loader, "_model", _FakeModel())

    r = client.post(
        "/v1/segment",
        files={"file": ("test.png", make_png_bytes(size=(80, 60)), "image/png")},
    )

    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"

    img = Image.open(io.BytesIO(r.content))
    assert img.size == (60, 80)  # PIL Image.size = (width, height)


def test_startup_lifecycle_runs_without_model():
    """Traverse le startup event (chargement du modèle, ici absent) sans planter."""
    with TestClient(app) as c:
        assert c.get("/health").status_code == 200
