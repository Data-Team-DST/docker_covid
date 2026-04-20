"""Logging configuration — writes JSON logs to tmp/logs/data-service.log."""
import logging
import logging.handlers
import os
from pathlib import Path


class _JSONFormatter(logging.Formatter):
    """One JSON object per line for easy grep/parsing."""

    def format(self, record: logging.LogRecord) -> str:
        import json
        import datetime

        payload = {
            "ts": datetime.datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        if hasattr(record, "extra"):
            payload.update(record.extra)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(log_dir: Path | None = None) -> None:
    """Configure root logger: console (INFO) + rotating file (DEBUG, JSON)."""
    if log_dir is None:
        project_root = Path(os.getenv("PROJECT_ROOT", "/app"))
        log_dir = project_root / "tmp" / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "data-service.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Console handler — plain text, INFO+
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s",
                          datefmt="%H:%M:%S")
    )

    # Rotating file handler — JSON, DEBUG+, 5 × 2 MB
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(_JSONFormatter())

    root.addHandler(console)
    root.addHandler(file_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
