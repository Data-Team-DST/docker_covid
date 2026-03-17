"""Point d'entrée FastAPI — DS_COVID ML Backend"""

import logging
from contextlib import asynccontextmanager

from app.api.health import router as health_router
from app.api.predict import router as predict_router
from app.config import settings
from app.models.loader import model_loader
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Chargement du modèle au démarrage, nettoyage à l'arrêt."""
    logger.info(f"Démarrage DS_COVID Backend v{settings.api_version}")
    logger.info(f"Chargement modèle depuis : {settings.model_path}")
    model_loader.load()
    if model_loader.is_loaded:
        logger.info("Modèle chargé avec succès")
    else:
        logger.warning("Modèle non chargé — /predict retournera 503")
    yield
    logger.info("Arrêt du backend")


app = FastAPI(
    title="DS_COVID — API d'inférence",
    description="Classification de radiographies pulmonaires (COVID / Normal / Pneumonie / Opacité)",
    version=settings.api_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en Phase 3
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, tags=["Health"])
app.include_router(predict_router, prefix="/api/v1", tags=["Prediction"])


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "DS_COVID API", "docs": "/docs", "health": "/health"}
