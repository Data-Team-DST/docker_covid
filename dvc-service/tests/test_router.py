import subprocess
from unittest.mock import patch

from fastapi.testclient import TestClient

from dvc_service import dvc_runner
from dvc_service.api.v1 import router as router_module
from dvc_service.main import app

client = TestClient(app)


def _fake_completed(returncode=0, stdout="ok", stderr=""):
    return subprocess.CompletedProcess(
        args=["dvc"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_dvc_status_success():
    with patch.object(dvc_runner.subprocess, "run", return_value=_fake_completed()):
        r = client.get("/v1/dvc/status")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["returncode"] == 0


def test_dvc_remotes():
    with patch.object(
        dvc_runner.subprocess, "run",
        return_value=_fake_completed(stdout="minio\tremote"),
    ):
        r = client.get("/v1/dvc/remotes")
    assert r.status_code == 200
    assert "minio" in r.json()["stdout"]


def test_dvc_pull_success(monkeypatch):
    monkeypatch.setattr(
        router_module, "_invalidate_data_service_cache", lambda: None
    )
    with patch.object(dvc_runner.subprocess, "run", return_value=_fake_completed()):
        r = client.post("/v1/dvc/pull")
    assert r.status_code == 200
    assert r.json()["success"] is True


def test_dvc_pull_missing_cache_files():
    with patch.object(
        dvc_runner.subprocess, "run",
        return_value=_fake_completed(returncode=1, stderr="Missing cache files"),
    ):
        r = client.post("/v1/dvc/pull")
    assert r.status_code == 404


def test_dvc_pull_generic_failure():
    with patch.object(
        dvc_runner.subprocess, "run",
        return_value=_fake_completed(returncode=1, stderr="boom"),
    ):
        r = client.post("/v1/dvc/pull")
    assert r.status_code == 500


def test_dvc_push_success():
    with patch.object(dvc_runner.subprocess, "run", return_value=_fake_completed()):
        r = client.post("/v1/dvc/push")
    assert r.status_code == 200


def test_dvc_push_failure():
    with patch.object(
        dvc_runner.subprocess, "run",
        return_value=_fake_completed(returncode=1, stderr="boom"),
    ):
        r = client.post("/v1/dvc/push")
    assert r.status_code == 500


def test_dvc_repro_success(monkeypatch):
    monkeypatch.setattr(
        router_module, "_invalidate_data_service_cache", lambda: None
    )
    with patch.object(dvc_runner.subprocess, "run", return_value=_fake_completed()):
        r = client.post("/v1/dvc/repro")
    assert r.status_code == 200


def test_dvc_repro_failure():
    with patch.object(
        dvc_runner.subprocess, "run",
        return_value=_fake_completed(returncode=1, stderr="boom"),
    ):
        r = client.post("/v1/dvc/repro")
    assert r.status_code == 500


def test_run_dvc_not_installed():
    with patch.object(dvc_runner.subprocess, "run", side_effect=FileNotFoundError):
        r = client.get("/v1/dvc/status")
    assert r.status_code == 500
    assert "installé" in r.json()["detail"]


def test_run_dvc_timeout():
    with patch.object(
        dvc_runner.subprocess, "run",
        side_effect=subprocess.TimeoutExpired(cmd="dvc", timeout=300),
    ):
        r = client.get("/v1/dvc/status")
    assert r.status_code == 504


def test_invalidate_data_service_cache_ignores_connection_error():
    """Best-effort : une invalidation qui échoue ne doit jamais faire planter
    la réponse de /pull (R8 — HTTP entre services, jamais bloquant)."""
    import requests as requests_module

    with patch.object(
        requests_module, "get", side_effect=requests_module.exceptions.ConnectionError
    ):
        router_module._invalidate_data_service_cache()  # ne doit pas lever
