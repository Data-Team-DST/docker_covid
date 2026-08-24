"""Middlewares HTTP — logging structuré des requêtes."""

import logging
import time

from fastapi import Request

logger = logging.getLogger(__name__)


async def log_requests(request: Request, call_next):
    """Log structuré de chaque requête HTTP (méthode, path, status, latence)."""
    t0 = time.time()
    response = await call_next(request)
    latency_ms = round((time.time() - t0) * 1000, 1)
    logger.info(
        "%s %s → %s  %.1fms",
        request.method,
        request.url.path,
        response.status_code,
        latency_ms,
    )
    return response
