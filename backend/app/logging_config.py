"""Configuration logging JSON structuré — DS_COVID Backend."""
import logging
import logging.handlers
import os
from pathlib import Path

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = Path(os.getenv("LOG_DIR", "/app/tmp/logs"))


class _JsonFormatter(logging.Formatter):
    """Formate chaque log en une ligne JSON."""

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime, timezone

        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> None:
    """Configure le logging JSON sur stdout + fichier rotatif (si accessible)."""
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)
    root.handlers.clear()

    stream = logging.StreamHandler()
    stream.setFormatter(_JsonFormatter())
    root.addHandler(stream)

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_DIR / "backend.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(_JsonFormatter())
        root.addHandler(file_handler)
    except (PermissionError, OSError):
        logging.getLogger(__name__).warning(
            "Impossible d'écrire les logs dans %s — stdout uniquement", LOG_DIR
        )
