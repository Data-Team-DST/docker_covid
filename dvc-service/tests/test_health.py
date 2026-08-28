from fastapi.testclient import TestClient

from dvc_service.main import app

client = TestClient(app)


def test_health_returns_200():
    r = client.get("/health")
    assert r.status_code == 200


def test_health_body():
    r = client.get("/health")
    body = r.json()
    assert body["status"] == "healthy"
    assert body["service"] == "dvc-service"
