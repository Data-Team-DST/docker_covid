"""Endpoint /explain — Grad-CAM, explique la prédiction (pas juste la segmentation).

Endpoint séparé de /predict (pas de champ optionnel dessus) : réutilisé à la demande
depuis demonstration/ (bouton dédié, pas automatique — évite de tripler la charge sur
segmentation-service à chaque classification, cf. TODO.md § Chantier jour J)."""

import logging

import httpx
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
)

from app.api.security import verify_api_key
from app.config import settings
from app.features.gradcam import compute_gradcam_png
from app.features.preprocessing import PreprocessOptions, preprocess_image
from app.models.loader import model_loader
from app.rate_limit import PREDICT_RATE_LIMIT, limiter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/explain",
    summary="Grad-CAM — zones de l'image ayant motivé la prédiction",
    responses={
        200: {"content": {"image/png": {}}},
        400: {"description": "Format ou taille d'image invalide"},
        401: {"description": "Clé API manquante ou invalide"},
        503: {"description": "Modèle non chargé"},
    },
)
@limiter.limit(PREDICT_RATE_LIMIT)
async def explain(
    request: Request,  # pylint: disable=unused-argument — requis par @limiter.limit
    file: UploadFile = File(
        ..., description="Radiographie thoracique au format JPEG ou PNG"
    ),
    _: None = Depends(verify_api_key),
):
    """Recalcule la classification et renvoie une heatmap Grad-CAM (PNG) superposée à
    l'image prétraitée — quelles zones ont pesé dans la décision, pas juste où sont
    les poumons (cf. /v1/segment côté segmentation-service, complémentaire)."""
    if not model_loader.is_loaded:
        raise HTTPException(status_code=503, detail="Modèle non disponible")

    if file.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(
            status_code=400, detail="Format accepté : JPEG ou PNG uniquement"
        )

    image_bytes = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop volumineux : {settings.max_upload_size_mb} Mo max",
        )

    try:
        img_array = preprocess_image(
            image_bytes,
            PreprocessOptions(
                img_size=settings.img_size,
                masking=settings.masking,
                cropping=settings.cropping,
                clahe=settings.clahe,
                clahe_clip_limit=settings.clahe_clip_limit,
                clahe_tile_grid_size=settings.clahe_tile_grid_size,
                denoising_method=settings.denoising_method,
                segmentation_service_url=settings.segmentation_service_url,
                segmentation_service_timeout_s=settings.segmentation_service_timeout_s,
            ),
        )
        png_bytes = compute_gradcam_png(model_loader.get_model(), img_array)
        return Response(content=png_bytes, media_type="image/png")

    except httpx.HTTPError as e:
        logger.error("Segmentation-service injoignable : %s", e)
        raise HTTPException(
            status_code=503, detail="Segmentation-service indisponible"
        ) from e

    except Exception as e:
        logger.error("Erreur Grad-CAM : %s", e)
        raise HTTPException(
            status_code=500, detail="Erreur interne lors du calcul Grad-CAM"
        ) from e
