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
            urllib.request.urlopen(req, timeout=2)
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
    http_handler = _AsyncHTTPHandler(service_name, LOG_SERVICE_URL)
    http_handler.setLevel(logging.WARNING)  # n'envoie que WARNING+ au central
    root.addHandler(http_handler)
