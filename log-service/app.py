"""Log-service — DS_COVID MLOps.

Reçoit les logs de tous les microservices (POST /v1/log),
les écrit dans tmp/logs/all.log + tmp/logs/{service}.log,
et permet de les requêter (GET /v1/logs).
"""
import json
import logging
import logging.handlers
import os
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Query
from pydantic import BaseModel

LOG_DIR = Path(os.getenv("LOG_DIR", "/app/tmp/logs"))
MAX_MEMORY = int(os.getenv("LOG_MEMORY_SIZE", "2000"))  # entrées gardées en RAM

LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── Handlers fichiers ──────────────────────────────────────────────────────────

def _file_handler(path: Path) -> logging.handlers.RotatingFileHandler:
    h = logging.handlers.RotatingFileHandler(
        path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    h.setFormatter(logging.Formatter("%(message)s"))
    return h


_all_handler = _file_handler(LOG_DIR / "all.log")
_service_handlers: dict[str, logging.handlers.RotatingFileHandler] = {}

# Buffer en mémoire pour GET /v1/logs (ring buffer)
_buffer: deque[dict] = deque(maxlen=MAX_MEMORY)


def _get_service_handler(service: str) -> logging.handlers.RotatingFileHandler:
    if service not in _service_handlers:
        safe = service.replace("/", "_").replace(".", "_")
        _service_handlers[service] = _file_handler(LOG_DIR / f"{safe}.log")
    return _service_handlers[service]


# ── App FastAPI ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="DS_COVID — Log Service",
    description="Agrégateur de logs pour tous les microservices DS_COVID.",
    version="1.0.0",
)

logging.basicConfig(level=logging.WARNING)  # logs internes du log-service uniquement


# ── Schémas ────────────────────────────────────────────────────────────────────

class LogEntry(BaseModel):
    service: str
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    logger: str
    msg: str
    ts: str | None = None
    extra: dict | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
def health():
    """État du log-service."""
    return {"status": "healthy", "buffered_entries": len(_buffer)}


@app.post(
    "/v1/log",
    status_code=204,
    tags=["Logs"],
    summary="Envoyer une entrée de log",
)
def receive_log(entry: LogEntry):
    """Reçoit une entrée de log depuis n'importe quel service."""
    payload = {
        "ts":      entry.ts or datetime.now(timezone.utc).isoformat(),
        "service": entry.service,
        "level":   entry.level,
        "logger":  entry.logger,
        "msg":     entry.msg,
    }
    if entry.extra:
        payload["extra"] = entry.extra

    line = json.dumps(payload, ensure_ascii=False)
    _all_handler.emit(logging.makeLogRecord({"msg": line, "args": ()}))
    _get_service_handler(entry.service).emit(
        logging.makeLogRecord({"msg": line, "args": ()})
    )
    _buffer.append(payload)


@app.get(
    "/v1/logs",
    tags=["Logs"],
    summary="Requêter les logs en mémoire",
    responses={200: {"content": {"application/json": {"example": {
        "total": 42,
        "entries": [{"ts": "2026-04-21T10:00:00Z", "service": "backend",
                     "level": "INFO", "logger": "app.main", "msg": "POST /predict → 200  245ms"}],
    }}}}},
)
def query_logs(
    service: str | None = Query(None, description="Filtrer par service (ex: backend)"),
    level:   str | None = Query(None, description="Filtrer par niveau (INFO, ERROR…)"),
    limit:   int        = Query(100,  description="Nombre max d'entrées", le=1000),
):
    """Retourne les dernières entrées de log (depuis le buffer en mémoire)."""
    entries = list(_buffer)
    if service:
        entries = [e for e in entries if e.get("service") == service]
    if level:
        entries = [e for e in entries if e.get("level") == level.upper()]
    entries = entries[-limit:]
    return {"total": len(entries), "entries": entries}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("LOG_SERVICE_PORT", "5002"))
    uvicorn.run(app, host="0.0.0.0", port=port)
