"""Cycle de vie de l'application — chargement du modèle au démarrage."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.models.loader import model_loader

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Chargement du modèle au démarrage, nettoyage à l'arrêt."""
    del fastapi_app
    logger.info("Démarrage DS_COVID Backend v%s", settings.api_version)
    logger.info(
        "Chargement modèle : MLflow Registry (%s@%s) puis fallback %s",
        settings.mlflow_model_name,
        settings.mlflow_model_stage,
        settings.model_path,
    )
    model_loader.load()
    if model_loader.is_loaded:
        logger.info("Modèle chargé avec succès (source: %s)", model_loader.source)
    else:
        logger.warning("Modèle non chargé — /predict retournera 503")
    yield
    logger.info("Arrêt du backend")
