"""Endpoint /predict — DS_COVID Backend"""

import logging
import time

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.metrics import stats
from app.api.security import verify_api_key
from app.config import settings
from app.features.preprocessing import preprocess_image
from app.models.loader import model_loader
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
        400: {"description": "Format image invalide (JPEG/PNG requis)"},
        401: {"description": "Clé API manquante ou invalide"},
        503: {"description": "Modèle non chargé"},
    },
)
async def predict(
    file: UploadFile = File(
        ..., description="Radiographie thoracique au format JPEG ou PNG"
    ),
    _: None = Depends(verify_api_key),
):
    """
    Classe une radiographie pulmonaire parmi 4 catégories :
    **COVID**, **Normal**, **Viral Pneumonia**, **Lung Opacity**.

    **Authentification** : header `X-API-Key` obligatoire.
    """
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

    try:
        t0 = time.time()
        image_bytes = await file.read()
        img_array = preprocess_image(image_bytes, settings.img_size)
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
        raise HTTPException(status_code=500, detail=f"Erreur interne : {str(e)}") from e
