"""Endpoint /health — DS_COVID Backend"""

from fastapi import APIRouter

from app.config import settings
from app.models.loader import model_loader

router = APIRouter()


@router.get("/health")
async def health():
    """Retourne l'état de santé du service et du modèle chargé."""
    return {
        "status": "healthy",
        "model_loaded": model_loader.is_loaded,
        "model_version": settings.model_version,
        "api_version": settings.api_version,
        "classes": settings.class_names,
    }
