"""Endpoint /metrics — exposition Prometheus-compatible (Phase 3)."""

import time

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.models.loader import model_loader

router = APIRouter(tags=["monitoring"])


class _RequestStats:
    """Compteur de métriques runtime (uptime + prédictions)."""

    def __init__(self):
        """Initialise le compteur au démarrage du module."""
        self.start_time = time.time()
        self.predict_count = 0

    def increment_predict(self) -> None:
        """Incrémente le compteur de prédictions."""
        self.predict_count += 1

    def uptime(self) -> float:
        """Retourne l'uptime en secondes."""
        return round(time.time() - self.start_time, 2)


stats = _RequestStats()


@router.get("/metrics", response_class=PlainTextResponse)
def get_metrics() -> str:
    """Métriques runtime au format Prometheus text.

    Expose : uptime, état du modèle, nombre de prédictions.
    Compatible Prometheus scrape (text/plain; version=0.0.4).
    """
    lines = [
        "# HELP ds_covid_uptime_seconds Uptime du backend en secondes",
        "# TYPE ds_covid_uptime_seconds gauge",
        f"ds_covid_uptime_seconds {stats.uptime()}",
        "# HELP ds_covid_model_loaded Modèle chargé (1=oui, 0=non)",
        "# TYPE ds_covid_model_loaded gauge",
        f"ds_covid_model_loaded {int(model_loader.is_loaded)}",
        "# HELP ds_covid_predictions_total Prédictions effectuées",
        "# TYPE ds_covid_predictions_total counter",
        f"ds_covid_predictions_total {stats.predict_count}",
    ]
    return "\n".join(lines) + "\n"
