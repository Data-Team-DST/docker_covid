"""Endpoint /metrics — exposition Prometheus native (US-18)."""

import time

from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from app.models.loader import model_loader

router = APIRouter(tags=["monitoring"])

uptime_seconds = Gauge("ds_covid_uptime_seconds", "Uptime du backend en secondes")
model_loaded = Gauge("ds_covid_model_loaded", "Modèle chargé (1=oui, 0=non)")
predictions_total = Counter("ds_covid_predictions_total", "Prédictions effectuées")
http_requests_total = Counter(
    "ds_covid_http_requests_total",
    "Requêtes HTTP reçues, par statut et route",
    ["status", "path"],
)
inference_latency_seconds = Histogram(
    "ds_covid_inference_latency_seconds", "Latence d'inférence en secondes"
)
auth_failures_total = Counter(
    "ds_covid_auth_failures_total", "Échecs d'authentification X-API-Key"
)
low_confidence_predictions_total = Counter(
    "ds_covid_low_confidence_predictions_total",
    "Prédictions dont la confiance est inférieure à 0.6",
)
predictions_by_class_total = Counter(
    "ds_covid_predictions_by_class_total",
    "Prédictions effectuées, par classe prédite",
    ["predicted_class"],
)


class _RequestStats:
    """Compteur runtime (uptime + prédictions) — alimente aussi Prometheus."""

    def __init__(self):
        """Initialise le compteur au démarrage du module."""
        self.start_time = time.time()
        self.predict_count = 0

    def increment_predict(self) -> None:
        """Incrémente le compteur de prédictions (interne + métrique Prometheus)."""
        self.predict_count += 1
        predictions_total.inc()

    def uptime(self) -> float:
        """Retourne l'uptime en secondes."""
        return round(time.time() - self.start_time, 2)


stats = _RequestStats()


@router.get("/metrics")
def get_metrics() -> Response:
    """Métriques runtime au format Prometheus text (via prometheus_client)."""
    uptime_seconds.set(stats.uptime())
    model_loaded.set(int(model_loader.is_loaded))
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
