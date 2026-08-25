import subprocess
from unittest.mock import patch

from fastapi.testclient import TestClient

from data_service.api.v1 import router as router_module
from data_service.main import app

client = TestClient(app)


# ── /v1/data/image ────────────────────────────────────────────────────────

def test_get_image_invalid_dataset():
    r = client.get("/v1/data/image", params={"dataset": "bogus", "path": "x.png"})
    assert r.status_code == 400


def test_get_image_missing_path():
    r = client.get("/v1/data/image", params={"dataset": "raw"})
    assert r.status_code == 400


def test_get_image_path_traversal_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(router_module, "DATA_DIR", tmp_path)
    r = client.get(
        "/v1/data/image",
        params={"dataset": "raw", "path": "../../etc/passwd"},
    )
    assert r.status_code == 400


def test_get_image_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(router_module, "DATA_DIR", tmp_path)
    (tmp_path / "raw").mkdir()
    r = client.get(
        "/v1/data/image",
        params={"dataset": "raw", "path": "missing.png"},
    )
    assert r.status_code == 404


def test_get_image_success(tmp_path, monkeypatch):
    monkeypatch.setattr(router_module, "DATA_DIR", tmp_path)
    raw = tmp_path / "raw"
    raw.mkdir()
    img = raw / "sample.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    r = client.get(
        "/v1/data/image",
        params={"dataset": "raw", "path": "sample.png"},
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"


# ── /v1/data/search ────────────────────────────────────────────────────────

def test_search_invalid_dataset():
    r = client.get("/v1/data/search", params={"dataset": "bogus", "query": "a"})
    assert r.status_code == 400


def test_search_missing_query():
    r = client.get("/v1/data/search", params={"dataset": "raw"})
    assert r.status_code == 400


def test_search_dataset_dir_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(router_module, "DATA_DIR", tmp_path)
    r = client.get("/v1/data/search", params={"dataset": "raw", "query": "covid"})
    assert r.status_code == 200
    body = r.json()
    assert body == {"results": [], "total": 0}


def test_search_fallback_scan_finds_match(tmp_path, monkeypatch):
    monkeypatch.setattr(router_module, "DATA_DIR", tmp_path)
    monkeypatch.setattr(router_module, "CACHE_FILE", tmp_path / "no_cache.json")
    raw = tmp_path / "raw" / "COVID"
    raw.mkdir(parents=True)
    (raw / "COVID-1.png").write_bytes(b"x")
    (raw / "Normal-1.png").write_bytes(b"x")

    r = client.get("/v1/data/search", params={"dataset": "raw", "query": "covid"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["results"][0]["filename"] == "COVID-1.png"
    assert body["results"][0]["label"] == "COVID"


# ── /v1/dvc/* ─────────────────────────────────────────────────────────────

def _fake_completed(returncode=0, stdout="ok", stderr=""):
    return subprocess.CompletedProcess(
        args=["dvc"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_dvc_status_success():
    with patch.object(router_module.subprocess, "run", return_value=_fake_completed()):
        r = client.get("/v1/dvc/status")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["returncode"] == 0


def test_dvc_remotes():
    with patch.object(
        router_module.subprocess, "run",
        return_value=_fake_completed(stdout="minio\tremote"),
    ):
        r = client.get("/v1/dvc/remotes")
    assert r.status_code == 200
    assert "minio" in r.json()["stdout"]


def test_dvc_pull_success(tmp_path, monkeypatch):
    cache_file = tmp_path / "data_cache.json"
    cache_file.write_text("{}")
    monkeypatch.setattr(router_module, "CACHE_FILE", cache_file)

    with patch.object(router_module.subprocess, "run", return_value=_fake_completed()):
        r = client.post("/v1/dvc/pull")

    assert r.status_code == 200
    assert r.json()["success"] is True
    assert not cache_file.exists()  # cache invalidé après un pull


def test_dvc_pull_missing_cache_files():
    with patch.object(
        router_module.subprocess, "run",
        return_value=_fake_completed(returncode=1, stderr="Missing cache files"),
    ):
        r = client.post("/v1/dvc/pull")
    assert r.status_code == 404


def test_dvc_pull_generic_failure():
    with patch.object(
        router_module.subprocess, "run",
        return_value=_fake_completed(returncode=1, stderr="boom"),
    ):
        r = client.post("/v1/dvc/pull")
    assert r.status_code == 500


def test_dvc_push_success():
    with patch.object(router_module.subprocess, "run", return_value=_fake_completed()):
        r = client.post("/v1/dvc/push")
    assert r.status_code == 200


def test_dvc_push_failure():
    with patch.object(
        router_module.subprocess, "run",
        return_value=_fake_completed(returncode=1, stderr="boom"),
    ):
        r = client.post("/v1/dvc/push")
    assert r.status_code == 500


def test_dvc_repro_success():
    with patch.object(router_module.subprocess, "run", return_value=_fake_completed()):
        r = client.post("/v1/dvc/repro")
    assert r.status_code == 200


def test_dvc_repro_failure():
    with patch.object(
        router_module.subprocess, "run",
        return_value=_fake_completed(returncode=1, stderr="boom"),
    ):
        r = client.post("/v1/dvc/repro")
    assert r.status_code == 500


def test_run_dvc_not_installed():
    with patch.object(router_module.subprocess, "run", side_effect=FileNotFoundError):
        r = client.get("/v1/dvc/status")
    assert r.status_code == 500
    assert "installé" in r.json()["detail"]


def test_run_dvc_timeout():
    with patch.object(
        router_module.subprocess, "run",
        side_effect=subprocess.TimeoutExpired(cmd="dvc", timeout=300),
    ):
        r = client.get("/v1/dvc/status")
    assert r.status_code == 504


# ── /v1/data/stats — refresh + cache ───────────────────────────────────────

def test_data_stats_refresh_bypasses_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(router_module, "DATA_DIR", tmp_path)
    monkeypatch.setattr(router_module, "CACHE_FILE", tmp_path / "cache.json")

    r = client.get("/v1/data/stats", params={"refresh": "true"})
    assert r.status_code == 200
    assert r.json()["cached"] is False


def test_data_stats_served_from_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(router_module, "DATA_DIR", tmp_path)
    monkeypatch.setattr(router_module, "CACHE_FILE", tmp_path / "cache.json")

    first = client.get("/v1/data/stats")
    assert first.json()["cached"] is False

    second = client.get("/v1/data/stats")
    assert second.json()["cached"] is True
