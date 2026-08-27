"""Endpoint /health — DS_COVID Backend"""

import logging

import httpx
from fastapi import APIRouter

from app.config import settings
from app.models.loader import model_loader

logger = logging.getLogger(__name__)
router = APIRouter()


def _segmentation_service_status() -> dict:
    """Ping rapide du segmentation-service (non bloquant longtemps : timeout court,
    échec silencieux — /health ne doit pas dépendre de la latence d'un autre
    service). Remonte aussi model_source pour observer d'où vient son modèle
    (MLflow Registry vs fichier local, cf. app/models/loader.py)."""
    try:
        response = httpx.get(
            f"{settings.segmentation_service_url}/health", timeout=2.0
        )
        if response.status_code != 200:
            return {"available": False, "model_source": None}
        payload = response.json()
        return {
            "available": bool(payload.get("model_loaded", False)),
            "model_source": payload.get("model_source"),
        }
    except httpx.HTTPError as e:
        logger.warning("segmentation-service injoignable : %s", e)
        return {"available": False, "model_source": None}


@router.get(
    "/health",
    summary="État du service",
    responses={200: {"content": {"application/json": {"example": {
        "status": "healthy",
        "model_loaded": True,
        "model_source": "registry",
        "segmentation_service_available": True,
        "segmentation_service_model_source": "local",
        "model_version": "1.0.0", "api_version": "1.0.0",
        "classes": ["COVID", "Lung_Opacity", "Normal", "Viral_Pneumonia"],
    }}}}},
)
async def health():
    """Retourne l'état de santé du service, du modèle de classification, et du
    segmentation-service (dépendance externe, cf. app/features/preprocessing.py)."""
    seg_status = _segmentation_service_status()
    return {
        "status": "healthy",
        "model_loaded": model_loader.is_loaded,
        "model_source": model_loader.source,
        "segmentation_service_available": seg_status["available"],
        "segmentation_service_model_source": seg_status["model_source"],
        "model_version": settings.model_version,
        "api_version": settings.api_version,
        "classes": settings.class_names,
    }
