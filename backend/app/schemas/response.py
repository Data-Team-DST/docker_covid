"""Schémas Pydantic — Réponses API"""

from pydantic import BaseModel, Field


class PredictionResponse(BaseModel):
    """Réponse de l'endpoint /predict : classe prédite, scores et latence."""

    predicted_class: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    scores: dict[str, float]
    latency_ms: float

    model_config = {
        "json_schema_extra": {
            "example": {
                "predicted_class": "COVID",
                "confidence": 0.92,
                "scores": {
                    "COVID": 0.92,
                    "Lung_Opacity": 0.04,
                    "Normal": 0.03,
                    "Viral_Pneumonia": 0.01,
                },
                "latency_ms": 245.3,
            }
        }
    }
