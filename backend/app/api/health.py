"""Endpoint /health — DS_COVID Backend"""

import logging

import httpx
from fastapi import APIRouter

from app.config import settings
from app.models.loader import model_loader

logger = logging.getLogger(__name__)
router = APIRouter()


def _segmentation_service_reachable() -> bool:
    """Ping rapide du segmentation-service (non bloquant longtemps : timeout court,
    échec silencieux — /health ne doit pas dépendre de la latence d'un autre
    service)."""
    try:
        response = httpx.get(
            f"{settings.segmentation_service_url}/health", timeout=2.0
        )
        healthy = response.status_code == 200
        return healthy and response.json().get("model_loaded", False)
    except httpx.HTTPError as e:
        logger.warning("segmentation-service injoignable : %s", e)
        return False


@router.get(
    "/health",
    summary="État du service",
    responses={200: {"content": {"application/json": {"example": {
        "status": "healthy",
        "model_loaded": True,
        "segmentation_service_available": True,
        "model_version": "1.0.0", "api_version": "1.0.0",
        "classes": ["COVID", "Lung_Opacity", "Normal", "Viral_Pneumonia"],
    }}}}},
)
async def health():
    """Retourne l'état de santé du service, du modèle de classification, et du
    segmentation-service (dépendance externe, cf. app/features/preprocessing.py)."""
    return {
        "status": "healthy",
        "model_loaded": model_loader.is_loaded,
        "segmentation_service_available": _segmentation_service_reachable(),
        "model_version": settings.model_version,
        "api_version": settings.api_version,
        "classes": settings.class_names,
    }
