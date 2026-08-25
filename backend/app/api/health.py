"""Endpoint /health — DS_COVID Backend"""

from fastapi import APIRouter

from app.config import settings
from app.models.loader import model_loader, segmentation_model_loader

router = APIRouter()


@router.get(
    "/health",
    summary="État du service",
    responses={200: {"content": {"application/json": {"example": {
        "status": "healthy", "model_loaded": True, "segmentation_model_loaded": True,
        "model_version": "1.0.0", "api_version": "1.0.0",
        "classes": ["COVID", "Lung_Opacity", "Normal", "Viral_Pneumonia"],
    }}}}},
)
async def health():
    """Retourne l'état de santé du service et des modèles chargés."""
    return {
        "status": "healthy",
        "model_loaded": model_loader.is_loaded,
        "segmentation_model_loaded": segmentation_model_loader.is_loaded,
        "model_version": settings.model_version,
        "api_version": settings.api_version,
        "classes": settings.class_names,
    }
