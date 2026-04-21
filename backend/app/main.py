"""Point d'entrée FastAPI — DS_COVID ML Backend"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.metrics import router as metrics_router
from app.api.predict import router as predict_router
from app.config import settings
from app.logging_config import setup_logging
from app.models.loader import model_loader

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Chargement du modèle au démarrage, nettoyage à l'arrêt."""
    del fastapi_app
    logger.info("Démarrage DS_COVID Backend v%s", settings.api_version)
    logger.info("Chargement modèle depuis : %s", settings.model_path)
    model_loader.load()
    if model_loader.is_loaded:
        logger.info("Modèle chargé avec succès")
    else:
        logger.warning("Modèle non chargé — /predict retournera 503")
    yield
    logger.info("Arrêt du backend")


app = FastAPI(
    title="DS_COVID — API d'inférence",
    description=(
        "Classification automatique de radiographies pulmonaires.\n\n"
        "**Classes** : COVID · Normal · Viral Pneumonia · Lung Opacity\n\n"
        "**Authentification** : header `X-API-Key` requis sur `/api/v1/predict`."
    ),
    version=settings.api_version,
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Health",     "description": "État du service et du modèle."},
        {"name": "Prediction", "description": "Inférence sur image radiographique."},
        {"name": "Monitoring", "description": "Métriques internes (compteurs)."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _log_requests(request: Request, call_next):
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


app.include_router(health_router, tags=["Health"])
app.include_router(predict_router, prefix="/api/v1", tags=["Prediction"])
app.include_router(metrics_router, tags=["Monitoring"])


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "DS_COVID API", "docs": "/docs", "health": "/health"}
