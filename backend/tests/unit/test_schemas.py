"""Tests unitaires — schémas Pydantic"""
import pytest
from pydantic import ValidationError

from app.schemas.response import PredictionResponse


def test_valid_prediction_response():
    data = PredictionResponse(
        predicted_class="COVID",
        confidence=0.92,
        scores={"COVID": 0.92, "Lung_Opacity": 0.04, "Normal": 0.03, "Viral_Pneumonia": 0.01},
        latency_ms=245.3,
    )
    assert data.predicted_class == "COVID"
    assert data.confidence == 0.92


def test_confidence_out_of_range():
    with pytest.raises(ValidationError):
        PredictionResponse(
            predicted_class="COVID",
            confidence=1.5,  # invalide : > 1.0
            scores={},
            latency_ms=100.0,
        )


def test_confidence_negative():
    with pytest.raises(ValidationError):
        PredictionResponse(
            predicted_class="Normal",
            confidence=-0.1,  # invalide : < 0
            scores={},
            latency_ms=100.0,
        )


def test_scores_serialization():
    data = PredictionResponse(
        predicted_class="Normal",
        confidence=0.88,
        scores={"COVID": 0.05, "Normal": 0.88, "Lung_Opacity": 0.04, "Viral_Pneumonia": 0.03},
        latency_ms=180.0,
    )
    serialized = data.model_dump()
    assert "scores" in serialized
    assert isinstance(serialized["scores"], dict)
