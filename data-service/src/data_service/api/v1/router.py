"""Router v1 — DS_COVID Data Service."""
import logging
import os
import subprocess
from pathlib import Path

import yaml
from fastapi import APIRouter, BackgroundTasks, HTTPException

logger = logging.getLogger(__name__)
api_router = APIRouter()

PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", "/app"))
DATA_DIR = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data")))


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
    full_cmd = ["dvc"] + cmd
    logger.info("dvc run: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            full_cmd,
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


# ── Data stats ─────────────────────────────────────────────────────────────

@api_router.get("/data/stats", tags=["data"])
def data_stats():
    """Statistiques des données : infos DVC + contenu physique des dossiers."""
    stats = {}
    for name in ("raw", "processed"):
        dvc_file = DATA_DIR / f"{name}.dvc"
        stats[name] = {
            "dvc": _dvc_file_info(dvc_file),
            "local": _local_dir_stats(DATA_DIR / name),
        }
    stats["models"] = {"local": _local_dir_stats(DATA_DIR / "models")}
    return stats


def _local_dir_stats(path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "nfiles": 0, "size_mb": 0}
    files = [f for f in path.rglob("*") if f.is_file()]
    return {
        "exists": True,
        "nfiles": len(files),
        "size_mb": round(
            sum(f.stat().st_size for f in files) / 1024 / 1024, 1
        ),
    }


# ── DVC opérations ─────────────────────────────────────────────────────────

@api_router.get("/dvc/status", tags=["dvc"])
def dvc_status():
    """Retourne le statut DVC (fichiers modifiés non committés)."""
    return _run_dvc(["status"])


@api_router.get("/dvc/remotes", tags=["dvc"])
def dvc_remotes():
    """Liste les remotes DVC configurés."""
    return _run_dvc(["remote", "list"])


@api_router.post("/dvc/pull", tags=["dvc"])
def dvc_pull(background_tasks: BackgroundTasks, target: str | None = None):
    """Lance dvc pull (optionnellement sur un target précis)."""
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
                )
            )
        raise HTTPException(
            status_code=500, detail=stderr or "dvc pull échoué"
        )
    return result


@api_router.post("/dvc/push", tags=["dvc"])
def dvc_push(target: str | None = None):
    """Lance dvc push."""
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
    """Rejoue le pipeline DVC complet (dvc repro)."""
    result = _run_dvc(["repro"])
    if not result["success"]:
        raise HTTPException(
            status_code=500, detail=result["stderr"] or "dvc repro échoué"
        )
    return result
