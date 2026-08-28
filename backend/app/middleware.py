"""Middlewares HTTP — logging structuré et métriques Prometheus des requêtes."""

import logging
import time

from fastapi import Request

from app.api.metrics import http_requests_total

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


async def track_http_metrics(request: Request, call_next):
    """Incrémente ds_covid_http_requests_total{status,path} pour chaque requête."""
    response = await call_next(request)
    http_requests_total.labels(
        status=str(response.status_code), path=request.url.path
    ).inc()
    return response
