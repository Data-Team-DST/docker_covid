"""Router v1 — DS_COVID Data Service."""
import json
import logging
import mimetypes
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)
api_router = APIRouter()

PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", "/app"))
DATA_DIR = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data")))
CACHE_FILE = PROJECT_ROOT / "tmp" / "data_cache.json"

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}
SKIP_EXTS = {".xlsx", ".xls", ".txt", ".csv", ".md"}


# ── Helpers ────────────────────────────────────────────────────────────────

def _dvc_file_info(dvc_path: Path) -> dict:
    if not dvc_path.exists():
        return {}
    with open(dvc_path, encoding="utf-8") as f:
        meta = yaml.safe_load(f)
    outs = meta.get("outs", [{}])[0]
    return {
        "md5": outs.get("md5", ""),
        "size_mb": round(outs.get("size", 0) / 1024 / 1024, 1),
        "nfiles": outs.get("nfiles"),
        "path": outs.get("path", ""),
        "dvc_file": dvc_path.name,
    }


def _run_dvc(cmd: list[str]) -> dict:
    logger.info("dvc run: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            ["dvc"] + cmd,
            capture_output=True, text=True,
            cwd=str(PROJECT_ROOT), timeout=300,
        )
        out = {
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "success": result.returncode == 0,
        }
        if out["success"]:
            logger.info("dvc %s OK (rc=0)", cmd[0])
        else:
            logger.warning(
                "dvc %s failed rc=%s stderr=%s",
                cmd[0], result.returncode, result.stderr.strip()[:200],
            )
        return out
    except FileNotFoundError:
        logger.error("dvc not found in container")
        raise HTTPException(
            status_code=500, detail="DVC non installé dans ce container"
        )
    except subprocess.TimeoutExpired:
        logger.error("dvc %s timeout after 300s", cmd[0])
        raise HTTPException(status_code=504, detail="DVC timeout (> 5 min)")


def _local_dir_stats(path: Path, build_index: bool = False) -> dict:
    if not path.exists():
        return {"exists": False, "nfiles": 0, "size_mb": 0, "labels": [], "index": []}
    files = [f for f in path.rglob("*") if f.is_file()
             and f.suffix.lower() not in SKIP_EXTS]
    labels = sorted({
        p.name for p in path.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    })
    result = {
        "exists": True,
        "nfiles": len(files),
        "size_mb": round(
            sum(f.stat().st_size for f in files) / 1024 / 1024, 1
        ),
        "labels": labels,
    }
    if build_index:
        index = []
        for f in files:
            if f.suffix.lower() in IMAGE_EXTS:
                rel = str(f.relative_to(path)).replace("\\", "/")
                parts = rel.split("/")
                index.append({"path": rel, "filename": f.name, "label": parts[0] if len(parts) > 1 else ""})
        result["index"] = index
    return result


def _current_dvc_hash() -> str:
    """Retourne le hash md5 du raw.dvc, ou '' si absent."""
    info = _dvc_file_info(DATA_DIR / "raw.dvc")
    return info.get("md5", "")


def _load_cache() -> dict | None:
    """Charge le cache JSON si le hash DVC n'a pas changé."""
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            cache = json.load(f)
        if cache.get("raw_hash") == _current_dvc_hash():
            return cache.get("stats")
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _save_cache(stats: dict) -> None:
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "raw_hash": _current_dvc_hash(),
                "computed_at": datetime.now(timezone.utc).isoformat(),
                "stats": stats,
            }, f, indent=2)
    except OSError:
        pass


# ── Data stats ─────────────────────────────────────────────────────────────

@api_router.get("/data/stats", tags=["data"])
def data_stats(refresh: bool = False):
    """Stats données avec cache JSON (invalidé si hash DVC change)."""
    if not refresh:
        cached = _load_cache()
        if cached is not None:
            logger.info("data_stats: served from cache")
            return {**cached, "cached": True}

    logger.info("data_stats: scanning filesystem...")
    stats: dict = {}
    for name in ("raw", "processed"):
        dvc_file = DATA_DIR / f"{name}.dvc"
        stats[name] = {
            "dvc": _dvc_file_info(dvc_file),
            "local": _local_dir_stats(DATA_DIR / name, build_index=(name == "raw")),
        }
    stats["models"] = {"local": _local_dir_stats(DATA_DIR / "models")}
    _save_cache(stats)
    return {**stats, "cached": False}


# ── Image preview ───────────────────────────────────────────────────────────

@api_router.get("/data/image", tags=["data"])
def get_image(
    dataset: str = "raw",
    path: str = "",
):
    """
    Sert une image depuis data/<dataset>/.
    Ex: /v1/data/image?dataset=raw&path=COVID-19_Radiography_Dataset/COVID/images/COVID-1.png
    """
    if dataset not in ("raw", "processed", "models"):
        raise HTTPException(status_code=400, detail="dataset invalide")
    if not path:
        raise HTTPException(status_code=400, detail="path requis")

    base = DATA_DIR / dataset
    candidate = (base / path).resolve()

    if not candidate.is_relative_to(base.resolve()):
        raise HTTPException(status_code=400, detail="path invalide")
    if not candidate.exists() or candidate.suffix.lower() not in IMAGE_EXTS:
        raise HTTPException(status_code=404, detail="Image introuvable")

    mime = mimetypes.guess_type(str(candidate))[0] or "image/png"
    return FileResponse(str(candidate), media_type=mime)


@api_router.get("/data/search", tags=["data"])
def search_images(
    dataset: str = "raw",
    query: str = "",
    limit: int = 20,
):
    """
    Cherche des images par nom dans data/<dataset>/ via index en cache.
    Retourne max `limit` chemins relatifs (depuis data/<dataset>/).
    """
    if dataset not in ("raw", "processed", "models"):
        raise HTTPException(status_code=400, detail="dataset invalide")
    if not query:
        raise HTTPException(status_code=400, detail="query requis")
    if limit > 100:
        limit = 100

    base = DATA_DIR / dataset
    if not base.exists():
        return {"results": [], "total": 0}

    q = query.lower()

    # Essayer de servir depuis l'index en cache
    cached = _load_cache()
    if cached and dataset in cached:
        index = cached[dataset].get("local", {}).get("index")
        if index is not None:
            results = [item for item in index if q in item["filename"].lower()]
            return {"results": results[:limit], "total": min(len(results), limit), "query": query}

    # Fallback : scan filesystem (index pas encore construit)
    results = []
    for f in base.rglob("*"):
        if f.is_file() and f.suffix.lower() in IMAGE_EXTS and q in f.name.lower():
            rel = str(f.relative_to(base)).replace("\\", "/")
            parts = rel.split("/")
            results.append({
                "path": rel,
                "filename": f.name,
                "label": parts[0] if len(parts) > 1 else "",
            })
            if len(results) >= limit:
                break

    return {"results": results, "total": len(results), "query": query}


# ── DVC opérations ─────────────────────────────────────────────────────────

@api_router.get("/dvc/status", tags=["dvc"])
def dvc_status():
    return _run_dvc(["status"])


@api_router.get("/dvc/remotes", tags=["dvc"])
def dvc_remotes():
    return _run_dvc(["remote", "list"])


@api_router.post("/dvc/pull", tags=["dvc"])
def dvc_pull(background_tasks: BackgroundTasks, target: str | None = None):
    cmd = ["pull"]
    if target:
        cmd.append(target)
    result = _run_dvc(cmd)
    if not result["success"]:
        stderr = result["stderr"] or ""
        if "Missing cache files" in stderr or "not in cache" in stderr:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Données absentes du remote MinIO — "
                    "faire dvc push depuis une machine avec data/raw/ complet"
                ),
            )
        raise HTTPException(
            status_code=500, detail=stderr or "dvc pull échoué"
        )
    # Invalider le cache stats après un pull
    if CACHE_FILE.exists():
        CACHE_FILE.unlink(missing_ok=True)
    return result


@api_router.post("/dvc/push", tags=["dvc"])
def dvc_push(target: str | None = None):
    cmd = ["push"]
    if target:
        cmd.append(target)
    result = _run_dvc(cmd)
    if not result["success"]:
        raise HTTPException(
            status_code=500, detail=result["stderr"] or "dvc push échoué"
        )
    return result


@api_router.post("/dvc/repro", tags=["dvc"])
def dvc_repro():
    result = _run_dvc(["repro"])
    if not result["success"]:
        raise HTTPException(
            status_code=500, detail=result["stderr"] or "dvc repro échoué"
        )
    return result
