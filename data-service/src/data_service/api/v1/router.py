"""Router v1 — DS_COVID Data Service (lecture seule : stats, recherche, images).

Les opérations DVC (pull/push/repro/status/remotes) vivent dans dvc-service
depuis le chantier point 16 — séparation lecture / mutation d'état local."""
import logging
import mimetypes
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from PIL import Image

from data_service.data_stats_service import (
    DATA_DIR,
    IMAGE_EXTS,
    dvc_file_info,
    load_cache,
    local_dir_stats,
    save_cache,
)
from data_service.image_metrics_service import (
    compute_image_metrics,
    mask_coverage,
    sample_images_from_class,
)

logger = logging.getLogger(__name__)
api_router = APIRouter()


# ── Data stats ─────────────────────────────────────────────────────────────

@api_router.get("/data/stats", tags=["data"])
def data_stats(refresh: bool = False):
    """Stats données avec cache JSON (invalidé si hash DVC change)."""
    if not refresh:
        cached = load_cache()
        if cached is not None:
            logger.info("data_stats: served from cache")
            return {**cached, "cached": True}

    logger.info("data_stats: scanning filesystem...")
    stats: dict = {}
    for name in ("raw", "processed"):
        dvc_file = DATA_DIR / f"{name}.dvc"
        stats[name] = {
            "dvc": dvc_file_info(dvc_file),
            "local": local_dir_stats(DATA_DIR / name, build_index=(name == "raw")),
        }
    stats["models"] = {"local": local_dir_stats(DATA_DIR / "models")}
    save_cache(stats)
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
    limit = min(limit, 100)

    base = DATA_DIR / dataset
    if not base.exists():
        return {"results": [], "total": 0}

    q = query.lower()

    # Essayer de servir depuis l'index en cache
    cached = load_cache()
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


@api_router.get("/data/sample", tags=["data"])
def sample_class_images(cls: str, n: int = 5):
    """
    Tire n images au hasard dans data/raw/COVID-19_Radiography_Dataset/<cls>/images/.
    Retourne des chemins relatifs utilisables tels quels par /v1/data/image et
    /v1/data/metrics. Porté depuis frontend/page/02_donnees (chantier point 15).
    """
    n = max(1, min(n, 20))
    raw_root = DATA_DIR / "raw" / "COVID-19_Radiography_Dataset"
    if not (raw_root / cls).exists():
        raise HTTPException(status_code=404, detail=f"Classe inconnue : {cls}")

    paths = sample_images_from_class(raw_root, cls, n)
    results = []
    for p in paths:
        rel = str(p.relative_to(raw_root)).replace("\\", "/")
        mask_rel = f"{cls}/masks/{p.name}"
        has_mask = (raw_root / cls / "masks" / p.name).exists()
        mask_path = f"COVID-19_Radiography_Dataset/{mask_rel}" if has_mask else None
        results.append({
            "path": f"COVID-19_Radiography_Dataset/{rel}",
            "mask_path": mask_path,
            "filename": p.name,
        })
    return {"class": cls, "images": results}


@api_router.get("/data/metrics", tags=["data"])
def image_metrics(path: str):
    """
    Calcule luminosité/contraste/entropie pour une image de data/raw/, et le
    taux de couverture du masque associé s'il existe. `path` : même format que
    /v1/data/image (relatif à data/raw/).
    """
    base = DATA_DIR / "raw"
    candidate = (base / path).resolve()
    if not candidate.is_relative_to(base.resolve()):
        raise HTTPException(status_code=400, detail="path invalide")
    if not candidate.exists() or candidate.suffix.lower() not in IMAGE_EXTS:
        raise HTTPException(status_code=404, detail="Image introuvable")

    img = Image.open(candidate)
    metrics = compute_image_metrics(img)

    images_marker = f"{os.sep}images{os.sep}"
    masks_marker = f"{os.sep}masks{os.sep}"
    mask_candidate = Path(str(candidate).replace(images_marker, masks_marker))
    coverage = mask_coverage(mask_candidate) if mask_candidate != candidate else None

    return {"path": path, "metrics": metrics, "mask_coverage": coverage}
