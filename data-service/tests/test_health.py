from fastapi.testclient import TestClient
from data_service.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"
    assert r.json()["service"] == "data-service"


def test_data_stats():
    r = client.get("/v1/data/stats")
    assert r.status_code == 200
    body = r.json()
    assert "raw" in body
    assert "processed" in body
    assert "models" in body
