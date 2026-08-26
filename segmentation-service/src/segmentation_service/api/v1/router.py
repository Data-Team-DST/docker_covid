"""Router v1 — Segmentation Service."""

import logging

from fastapi import APIRouter, File, HTTPException, Response, UploadFile

from segmentation_service.config import settings
from segmentation_service.model import model_loader, predict_lung_mask

logger = logging.getLogger(__name__)
api_router = APIRouter()


@api_router.post(
    "/segment",
    tags=["segmentation"],
    summary="Prédire le mask pulmonaire d'une radiographie",
    responses={
        200: {"content": {"image/png": {}}},
        400: {"description": "Image illisible"},
        503: {"description": "Modèle non chargé"},
    },
)
async def segment(
    file: UploadFile = File(..., description="Radiographie thoracique (JPEG/PNG)"),
):
    """
    Prédit le mask binaire des poumons via le U-Net et le renvoie en PNG, aux mêmes
    dimensions que l'image reçue (redimensionnement géré côté service).
    """
    if not model_loader.is_loaded:
        raise HTTPException(status_code=503, detail="Modèle de segmentation non chargé")

    image_bytes = await file.read()

    try:
        mask_png = predict_lung_mask(
            image_bytes,
            img_size=settings.img_size,
            clean_components=settings.clean_mask_components,
            clean_kernel=settings.clean_mask_closing_kernel,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Erreur segmentation : %s", e)
        raise HTTPException(
            status_code=500, detail="Erreur interne lors de la segmentation"
        ) from e

    return Response(content=mask_png, media_type="image/png")
