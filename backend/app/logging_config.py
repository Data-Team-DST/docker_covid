"""Configuration logging — DS_COVID Backend.

Logs JSON structurés sur stdout + fichier rotatif tmp/logs/backend.log (si
accessible) + envoi asynchrone non-bloquant au log-service central (si
disponible).

Dupliqué depuis l'ancien shared/logging_config.py (2026-08-24, US-23) : ce
module était importé directement par backend/ et data-service/ via un
bind-mount Docker Compose, ce qui cassait le build des images hors Compose
(K8s notamment — aucune image ne copiait shared/ au build). Dupliquer ce
petit module (~100 lignes, change rarement) restaure l'autonomie de build de
chaque service, conformément aux frontières de service du projet.
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import threading
from datetime import UTC, datetime
from pathlib import Path

LOG_LEVEL       = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR         = Path(os.getenv("LOG_DIR", "/app/tmp/logs"))
LOG_SERVICE_URL = os.getenv("LOG_SERVICE_URL", "http://log-service:5002/v1/log")

# Logger dédié à la télémétrie de prédiction (scores par classe), consommé par
# trainer/scripts/drift_report.py via GET /v1/logs sur le log-service — voir US-20.
TELEMETRY_LOGGER_NAME = "app.predict.telemetry"


class _JsonFormatter(logging.Formatter):
    """Formatte chaque log en une ligne JSON structurée."""

    def __init__(self, service_name: str) -> None:
        super().__init__()
        self._service = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts":      datetime.now(UTC).isoformat(),
            "service": self._service,
            "level":   record.levelname,
            "logger":  record.name,
            "msg":     record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class _LoggerNameFilter(logging.Filter):
    """Filtre les enregistrements par nom de logger exact (inclusion ou exclusion)."""

    def __init__(self, logger_name: str, *, exclude: bool = False) -> None:
        super().__init__()
        self._logger_name = logger_name
        self._exclude = exclude

    def filter(self, record: logging.LogRecord) -> bool:
        matches = record.name == self._logger_name
        return not matches if self._exclude else matches


class _AsyncHTTPHandler(logging.Handler):
    """Envoie les logs au log-service dans un thread daemon (non-bloquant)."""

    def __init__(self, service_name: str, url: str) -> None:
        super().__init__()
        self._service = service_name
        self._url = url

    def emit(self, record: logging.LogRecord) -> None:
        payload = {
            "service": self._service,
            "level":   record.levelname,
            "logger":  record.name,
            "msg":     record.getMessage(),
            "ts":      datetime.now(UTC).isoformat(),
        }
        extra_data = getattr(record, "extra_data", None)
        if extra_data:
            payload["extra"] = extra_data
        threading.Thread(target=self._post, args=(payload,), daemon=True).start()

    def _post(self, payload: dict) -> None:
        try:
            import urllib.request
            data = json.dumps(payload).encode()
            req  = urllib.request.Request(
                self._url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=2):
                pass
        except Exception:  # noqa: BLE001
            pass  # log-service indisponible → on ignore silencieusement


def setup_logging() -> None:
    """Configure stdout JSON + fichier rotatif + envoi log-service central."""
    service_name = "backend"
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)
    root.handlers.clear()

    fmt = _JsonFormatter(service_name)

    # 1. Stdout
    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    root.addHandler(stream)

    # 2. Fichier rotatif local : tmp/logs/{service_name}.log
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            LOG_DIR / f"{service_name}.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except (PermissionError, OSError):
        logging.getLogger(__name__).warning(
            "Logs fichier inaccessibles (%s) — stdout uniquement", LOG_DIR
        )

    # 3. Log-service central (non-bloquant, silencieux si indisponible)
    #    WARNING+ pour tous les loggers, sauf la télémétrie de prédiction qui a
    #    son propre handler (point 4) pour ne pas la dupliquer ici.
    http_handler = _AsyncHTTPHandler(service_name, LOG_SERVICE_URL)
    http_handler.setLevel(logging.WARNING)
    http_handler.addFilter(_LoggerNameFilter(TELEMETRY_LOGGER_NAME, exclude=True))
    root.addHandler(http_handler)

    # 4. Télémétrie de prédiction (INFO, scores par classe) → log-service,
    #    uniquement pour TELEMETRY_LOGGER_NAME (voir app/api/predict.py).
    telemetry_handler = _AsyncHTTPHandler(service_name, LOG_SERVICE_URL)
    telemetry_handler.setLevel(logging.INFO)
    telemetry_handler.addFilter(_LoggerNameFilter(TELEMETRY_LOGGER_NAME))
    root.addHandler(telemetry_handler)
