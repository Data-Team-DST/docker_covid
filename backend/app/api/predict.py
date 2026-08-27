# code-smell: max-lines=145 reason="Doc OpenAPI (responses=) + gestion d'erreurs multi-services (classifieur + segmentation-service) + télémétrie US-20"
"""Endpoint /predict — DS_COVID Backend"""

import logging
import time

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.api.metrics import (
    inference_latency_seconds,
    low_confidence_predictions_total,
    predictions_by_class_total,
    stats,
)
from app.api.security import verify_api_key
from app.config import settings
from app.features.preprocessing import preprocess_image
from app.logging_config import TELEMETRY_LOGGER_NAME
from app.models.loader import model_loader
from app.rate_limit import limiter, predict_rate_limit
from app.schemas.response import PredictionResponse

logger = logging.getLogger(__name__)
telemetry_logger = logging.getLogger(TELEMETRY_LOGGER_NAME)
router = APIRouter()


@router.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Classifier une radiographie pulmonaire",
    responses={
        200: {"content": {"application/json": {"example": {
            "predicted_class": "COVID",
            "confidence": 0.92,
            "scores": {"COVID": 0.92, "Lung_Opacity": 0.04,
                       "Normal": 0.03, "Viral_Pneumonia": 0.01},
            "latency_ms": 245.3,
        }}}},
        400: {"description": "Format ou taille d'image invalide (JPEG/PNG, "
                              f"{settings.max_upload_size_mb} Mo max)"},
        401: {"description": "Clé API manquante ou invalide"},
        429: {"description": "Trop de requêtes — limite de "
                              f"{settings.rate_limit_per_minute}/min dépassée"},
        503: {"description": "Modèle non chargé"},
    },
)
@limiter.limit(predict_rate_limit)
async def predict(
    request: Request,
    file: UploadFile = File(
        ..., description="Radiographie thoracique au format JPEG ou PNG"
    ),
    _: None = Depends(verify_api_key),
):
    """
    Classe une radiographie pulmonaire parmi 4 catégories :
    **COVID**, **Normal**, **Viral Pneumonia**, **Lung Opacity**.

    **Authentification** : header `X-API-Key` obligatoire.
    **Limite** : 100 requêtes/minute par client (configurable via `RATE_LIMIT_PER_MINUTE`).
    """
    # `request` est inutilisé ici mais requis par le décorateur @limiter.limit
    if not model_loader.is_loaded:
        raise HTTPException(
            status_code=503,
            detail=(
                "Modèle non disponible — vérifier que"
                " data/models/ contient le .keras"
            ),
        )

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
        t0 = time.time()
        img_array = preprocess_image(
            image_bytes,
            img_size=settings.img_size,
            masking=settings.masking,
            cropping=settings.cropping,
            clahe=settings.clahe,
            clahe_clip_limit=settings.clahe_clip_limit,
            clahe_tile_grid_size=settings.clahe_tile_grid_size,
            denoising_method=settings.denoising_method,
            segmentation_service_url=settings.segmentation_service_url,
            segmentation_service_timeout_s=settings.segmentation_service_timeout_s,
        )
        predictions = model_loader.predict(img_array)
        elapsed_s = time.time() - t0
        latency_ms = round(elapsed_s * 1000, 1)

        predicted_idx = int(predictions.argmax())
        predicted_class = settings.class_names[predicted_idx]
        confidence = float(predictions[predicted_idx])

        scores = {
            cls: float(predictions[i]) for i, cls in enumerate(settings.class_names)
        }

        stats.increment_predict()
        inference_latency_seconds.observe(elapsed_s)
        predictions_by_class_total.labels(predicted_class=predicted_class).inc()
        if confidence < 0.6:
            low_confidence_predictions_total.inc()
        logger.info(
            "Prédiction : %s (%.1f%%) | %sms",
            predicted_class,
            confidence * 100,
            latency_ms,
        )
        telemetry_logger.info(
            "prediction",
            extra={"extra_data": {
                "predicted_class": predicted_class,
                "confidence": confidence,
                "scores": scores,
                "latency_ms": latency_ms,
            }},
        )

        return PredictionResponse(
            predicted_class=predicted_class,
            confidence=confidence,
            scores=scores,
            latency_ms=latency_ms,
        )

    except httpx.HTTPError as e:
        logger.error("Segmentation-service injoignable : %s", e)
        raise HTTPException(
            status_code=503, detail="Segmentation-service indisponible"
        ) from e

    except Exception as e:
        logger.error("Erreur prédiction : %s", e)
        raise HTTPException(
            status_code=500, detail="Erreur interne lors de la prédiction"
        ) from e
