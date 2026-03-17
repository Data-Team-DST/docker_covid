"""Endpoint /predict — DS_COVID Backend"""

import logging
import time

from app.config import settings
from app.features.preprocessing import preprocess_image
from app.models.loader import model_loader
from app.schemas.response import PredictionResponse
from fastapi import APIRouter, File, HTTPException, UploadFile

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/predict", response_model=PredictionResponse)
async def predict(file: UploadFile = File(...)):
    """
    Prédit la classe d'une radiographie pulmonaire.

    - **file**: image JPEG ou PNG (radiographie thoracique)
    - **Retourne**: classe prédite + scores de confiance pour les 4 classes
    """
    if not model_loader.is_loaded:
        raise HTTPException(
            status_code=503,
            detail="Modèle non disponible — vérifier que data/models/ contient le fichier .keras",
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
            cls: float(predictions[i])
            for i, cls in enumerate(settings.class_names)
        }

        logger.info(
            f"Prédiction : {predicted_class} ({confidence:.1%}) | {latency_ms}ms"
        )

        return PredictionResponse(
            predicted_class=predicted_class,
            confidence=confidence,
            scores=scores,
            latency_ms=latency_ms,
        )

    except Exception as e:
        logger.error(f"Erreur prédiction : {e}")
        raise HTTPException(
            status_code=500, detail=f"Erreur interne : {str(e)}"
        ) from e
