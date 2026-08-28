"""Stats et cache JSON sur data/ (raw/processed/models) — extrait du router
pour respecter la limite de taille/rôle des fichiers `*_router.py`."""

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", "/app"))

DATA_DIR = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data")))
CACHE_FILE = PROJECT_ROOT / "tmp" / "data_cache.json"

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}
SKIP_EXTS = {".xlsx", ".xls", ".txt", ".csv", ".md"}


def dvc_file_info(dvc_path: Path) -> dict:
    """Lit un fichier .dvc et retourne son hash/taille/nombre de fichiers."""
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


def local_dir_stats(path: Path, build_index: bool = False) -> dict:
    """Scanne un dossier local et retourne nombre/taille/labels (+ index images)."""
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


def current_dvc_hash() -> str:
    """Retourne le hash md5 du raw.dvc, ou '' si absent."""
    info = dvc_file_info(DATA_DIR / "raw.dvc")
    return info.get("md5", "")


def load_cache() -> dict | None:
    """Charge le cache JSON si le hash DVC n'a pas changé."""
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            cache = json.load(f)
        if cache.get("raw_hash") == current_dvc_hash():
            return cache.get("stats")
    except (json.JSONDecodeError, OSError):
        pass
    return None


def save_cache(stats: dict) -> None:
    """Sauvegarde les stats calculées avec le hash DVC courant."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "raw_hash": current_dvc_hash(),
                "computed_at": datetime.now(UTC).isoformat(),
                "stats": stats,
            }, f, indent=2)
    except OSError:
        pass
