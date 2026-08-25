"""Endpoint /predict — DS_COVID Backend"""

import logging
import time

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.api.metrics import stats
from app.api.security import verify_api_key
from app.config import settings
from app.features.preprocessing import preprocess_image
from app.models.loader import model_loader, segmentation_model_loader
from app.rate_limit import limiter, predict_rate_limit
from app.schemas.response import PredictionResponse

logger = logging.getLogger(__name__)
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

    # Le masking (mask généré par le U-Net) fait partie du pipeline de preprocessing
    # utilisé à l'entraînement (cf. params.yaml preprocess.masking) : sans lui, les
    # images envoyées au classifieur ne ressembleraient pas à ce qu'il a appris
    # (train/serving skew) — on refuse plutôt que de prédire silencieusement en dégradé.
    if settings.masking and not segmentation_model_loader.is_loaded:
        raise HTTPException(
            status_code=503,
            detail=(
                "Modèle de segmentation non disponible — vérifier que"
                " data/models/ contient le U-Net"
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
            segmentation_model=segmentation_model_loader if segmentation_model_loader.is_loaded else None,
            masking=settings.masking,
            cropping=settings.cropping,
            clahe=settings.clahe,
            clahe_clip_limit=settings.clahe_clip_limit,
            clahe_tile_grid_size=settings.clahe_tile_grid_size,
            denoising_method=settings.denoising_method,
            clean_mask_components=settings.clean_mask_components,
            clean_mask_closing_kernel=settings.clean_mask_closing_kernel,
        )
        predictions = model_loader.predict(img_array)
        latency_ms = round((time.time() - t0) * 1000, 1)

        predicted_idx = int(predictions.argmax())
        predicted_class = settings.class_names[predicted_idx]
        confidence = float(predictions[predicted_idx])

        scores = {
            cls: float(predictions[i]) for i, cls in enumerate(settings.class_names)
        }

        stats.increment_predict()
        logger.info(
            "Prédiction : %s (%.1f%%) | %sms",
            predicted_class,
            confidence * 100,
            latency_ms,
        )

        return PredictionResponse(
            predicted_class=predicted_class,
            confidence=confidence,
            scores=scores,
            latency_ms=latency_ms,
        )

    except Exception as e:
        logger.error("Erreur prédiction : %s", e)
        raise HTTPException(
            status_code=500, detail="Erreur interne lors de la prédiction"
        ) from e
