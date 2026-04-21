"""Configuration logging partagée — DS_COVID MLOps.

Usage (dans n'importe quel service) :
    from shared.logging_config import setup_logging
    setup_logging(service_name="backend")

Comportement :
  - Logs JSON structurés sur stdout
  - Fichier rotatif tmp/logs/{service_name}.log (si accessible)
  - Envoi asynchrone non-bloquant au log-service central (si disponible)
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

LOG_LEVEL       = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR         = Path(os.getenv("LOG_DIR", "/app/tmp/logs"))
LOG_SERVICE_URL = os.getenv("LOG_SERVICE_URL", "http://log-service:5002/v1/log")


# ── Formatter JSON ─────────────────────────────────────────────────────────────

class _JsonFormatter(logging.Formatter):
    def __init__(self, service_name: str) -> None:
        super().__init__()
        self._service = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts":      datetime.now(timezone.utc).isoformat(),
            "service": self._service,
            "level":   record.levelname,
            "logger":  record.name,
            "msg":     record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


# ── Handler HTTP non-bloquant ──────────────────────────────────────────────────

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
            "ts":      datetime.now(timezone.utc).isoformat(),
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
        except Exception:
            pass  # log-service indisponible → on ignore silencieusement


# ── Point d'entrée public ──────────────────────────────────────────────────────

def setup_logging(service_name: str) -> None:
    """Configure stdout JSON + fichier rotatif + envoi log-service central."""
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
