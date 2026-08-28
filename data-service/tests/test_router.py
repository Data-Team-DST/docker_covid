import subprocess
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from data_service import data_stats_service, dvc_service
from data_service.api.v1 import router as router_module
from data_service.main import app

client = TestClient(app)


def _patch_data_dir(monkeypatch, path):
    """DATA_DIR est importé dans router.py ET utilisé en interne par
    data_stats_service (load_cache/save_cache/current_dvc_hash) — patcher les
    deux pour que le cache calcule bien son hash sur le tmp_path du test (piège
    documenté dans import_cascade.md R13 : patcher un module qui a juste
    réimporté un nom ne suffit pas si la fonction réelle vit ailleurs)."""
    monkeypatch.setattr(router_module, "DATA_DIR", path)
    monkeypatch.setattr(data_stats_service, "DATA_DIR", path)


def _patch_cache_file(monkeypatch, path):
    """Même piège que _patch_data_dir, pour CACHE_FILE."""
    monkeypatch.setattr(router_module, "CACHE_FILE", path)
    monkeypatch.setattr(data_stats_service, "CACHE_FILE", path)


# ── /v1/data/image ────────────────────────────────────────────────────────

def test_get_image_invalid_dataset():
    r = client.get("/v1/data/image", params={"dataset": "bogus", "path": "x.png"})
    assert r.status_code == 400


def test_get_image_missing_path():
    r = client.get("/v1/data/image", params={"dataset": "raw"})
    assert r.status_code == 400


def test_get_image_path_traversal_rejected(tmp_path, monkeypatch):
    _patch_data_dir(monkeypatch, tmp_path)
    r = client.get(
        "/v1/data/image",
        params={"dataset": "raw", "path": "../../etc/passwd"},
    )
    assert r.status_code == 400


def test_get_image_not_found(tmp_path, monkeypatch):
    _patch_data_dir(monkeypatch, tmp_path)
    (tmp_path / "raw").mkdir()
    r = client.get(
        "/v1/data/image",
        params={"dataset": "raw", "path": "missing.png"},
    )
    assert r.status_code == 404


def test_get_image_success(tmp_path, monkeypatch):
    _patch_data_dir(monkeypatch, tmp_path)
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
    _patch_data_dir(monkeypatch, tmp_path)
    r = client.get("/v1/data/search", params={"dataset": "raw", "query": "covid"})
    assert r.status_code == 200
    body = r.json()
    assert body == {"results": [], "total": 0}


def test_search_fallback_scan_finds_match(tmp_path, monkeypatch):
    _patch_data_dir(monkeypatch, tmp_path)
    _patch_cache_file(monkeypatch, tmp_path / "no_cache.json")
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


# ── /v1/data/sample & /v1/data/metrics ──────────────────────────────────────

def _make_raw_class(tmp_path, cls: str, with_mask: bool = True):
    raw_root = tmp_path / "raw" / "COVID-19_Radiography_Dataset"
    images_dir = raw_root / cls / "images"
    images_dir.mkdir(parents=True)
    img_path = images_dir / f"{cls}-1.png"
    Image.new("RGB", (10, 10), color=(50, 50, 50)).save(img_path)
    if with_mask:
        masks_dir = raw_root / cls / "masks"
        masks_dir.mkdir(parents=True)
        Image.new("L", (10, 10), color=255).save(masks_dir / f"{cls}-1.png")
    return raw_root


def test_sample_class_images_unknown_class(tmp_path, monkeypatch):
    _patch_data_dir(monkeypatch, tmp_path)
    (tmp_path / "raw" / "COVID-19_Radiography_Dataset").mkdir(parents=True)
    r = client.get("/v1/data/sample", params={"cls": "Bogus"})
    assert r.status_code == 404


def test_sample_class_images_success_with_mask(tmp_path, monkeypatch):
    _patch_data_dir(monkeypatch, tmp_path)
    _make_raw_class(tmp_path, "COVID")

    r = client.get("/v1/data/sample", params={"cls": "COVID", "n": 5})

    assert r.status_code == 200
    body = r.json()
    assert body["class"] == "COVID"
    assert len(body["images"]) == 1
    assert body["images"][0]["mask_path"] is not None


def test_image_metrics_success(tmp_path, monkeypatch):
    _patch_data_dir(monkeypatch, tmp_path)
    _make_raw_class(tmp_path, "COVID")

    r = client.get(
        "/v1/data/metrics",
        params={"path": "COVID-19_Radiography_Dataset/COVID/images/COVID-1.png"},
    )

    assert r.status_code == 200
    body = r.json()
    assert body["metrics"]["luminosity_mean"] == 50.0
    assert body["mask_coverage"] == 100.0


def test_image_metrics_not_found(tmp_path, monkeypatch):
    _patch_data_dir(monkeypatch, tmp_path)
    (tmp_path / "raw").mkdir()
    r = client.get("/v1/data/metrics", params={"path": "missing.png"})
    assert r.status_code == 404


def test_image_metrics_path_traversal_rejected(tmp_path, monkeypatch):
    _patch_data_dir(monkeypatch, tmp_path)
    (tmp_path / "raw").mkdir()
    r = client.get("/v1/data/metrics", params={"path": "../../etc/passwd"})
    assert r.status_code == 400


# ── /v1/dvc/* ─────────────────────────────────────────────────────────────

def _fake_completed(returncode=0, stdout="ok", stderr=""):
    return subprocess.CompletedProcess(
        args=["dvc"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_dvc_status_success():
    with patch.object(dvc_service.subprocess, "run", return_value=_fake_completed()):
        r = client.get("/v1/dvc/status")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["returncode"] == 0


def test_dvc_remotes():
    with patch.object(
        dvc_service.subprocess, "run",
        return_value=_fake_completed(stdout="minio\tremote"),
    ):
        r = client.get("/v1/dvc/remotes")
    assert r.status_code == 200
    assert "minio" in r.json()["stdout"]


def test_dvc_pull_success(tmp_path, monkeypatch):
    cache_file = tmp_path / "data_cache.json"
    cache_file.write_text("{}")
    _patch_cache_file(monkeypatch, cache_file)

    with patch.object(dvc_service.subprocess, "run", return_value=_fake_completed()):
        r = client.post("/v1/dvc/pull")

    assert r.status_code == 200
    assert r.json()["success"] is True
    assert not cache_file.exists()  # cache invalidé après un pull


def test_dvc_pull_missing_cache_files():
    with patch.object(
        dvc_service.subprocess, "run",
        return_value=_fake_completed(returncode=1, stderr="Missing cache files"),
    ):
        r = client.post("/v1/dvc/pull")
    assert r.status_code == 404


def test_dvc_pull_generic_failure():
    with patch.object(
        dvc_service.subprocess, "run",
        return_value=_fake_completed(returncode=1, stderr="boom"),
    ):
        r = client.post("/v1/dvc/pull")
    assert r.status_code == 500


def test_dvc_push_success():
    with patch.object(dvc_service.subprocess, "run", return_value=_fake_completed()):
        r = client.post("/v1/dvc/push")
    assert r.status_code == 200


def test_dvc_push_failure():
    with patch.object(
        dvc_service.subprocess, "run",
        return_value=_fake_completed(returncode=1, stderr="boom"),
    ):
        r = client.post("/v1/dvc/push")
    assert r.status_code == 500


def test_dvc_repro_success():
    with patch.object(dvc_service.subprocess, "run", return_value=_fake_completed()):
        r = client.post("/v1/dvc/repro")
    assert r.status_code == 200


def test_dvc_repro_failure():
    with patch.object(
        dvc_service.subprocess, "run",
        return_value=_fake_completed(returncode=1, stderr="boom"),
    ):
        r = client.post("/v1/dvc/repro")
    assert r.status_code == 500


def test_run_dvc_not_installed():
    with patch.object(dvc_service.subprocess, "run", side_effect=FileNotFoundError):
        r = client.get("/v1/dvc/status")
    assert r.status_code == 500
    assert "installé" in r.json()["detail"]


def test_run_dvc_timeout():
    with patch.object(
        dvc_service.subprocess, "run",
        side_effect=subprocess.TimeoutExpired(cmd="dvc", timeout=300),
    ):
        r = client.get("/v1/dvc/status")
    assert r.status_code == 504


# ── /v1/data/stats — refresh + cache ───────────────────────────────────────

def test_data_stats_refresh_bypasses_cache(tmp_path, monkeypatch):
    _patch_data_dir(monkeypatch, tmp_path)
    _patch_cache_file(monkeypatch, tmp_path / "cache.json")

    r = client.get("/v1/data/stats", params={"refresh": "true"})
    assert r.status_code == 200
    assert r.json()["cached"] is False


def test_data_stats_served_from_cache(tmp_path, monkeypatch):
    _patch_data_dir(monkeypatch, tmp_path)
    _patch_cache_file(monkeypatch, tmp_path / "cache.json")

    first = client.get("/v1/data/stats")
    assert first.json()["cached"] is False

    second = client.get("/v1/data/stats")
    assert second.json()["cached"] is True
