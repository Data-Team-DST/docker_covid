"""DS_COVID — Segmentation Service : prédit le mask pulmonaire (U-Net).

Isolé du backend de classification pour que les deux services restent
déployables/scalables indépendamment : le backend n'a pas besoin d'embarquer
le poids du U-Net (et TensorFlow) rien que pour du preprocessing d'inférence,
et ce service peut être redéployé/rescalé sans toucher au backend.
"""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from segmentation_service.api.v1.router import api_router
from segmentation_service.config import settings
from segmentation_service.logging_config import setup_logging
from segmentation_service.model import model_loader

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DS_COVID — Segmentation Service",
    description="Prédiction du mask pulmonaire (U-Net) pour le preprocessing d'inférence.",
    version=settings.model_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup():
    logger.info("segmentation-service démarrage, chargement depuis %s", settings.model_path)
    model_loader.load(settings.model_path)
    if model_loader.is_loaded:
        logger.info("U-Net chargé avec succès")
    else:
        logger.warning("U-Net non chargé — /v1/segment retournera 503")


@app.get("/health", tags=["health"])
def health():
    return {
        "status": "healthy",
        "service": "segmentation-service",
        "version": settings.model_version,
        "model_loaded": model_loader.is_loaded,
    }


app.include_router(api_router, prefix="/v1")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "segmentation_service.main:app",
        host="0.0.0.0",
        port=int(os.getenv("SEGMENTATION_SERVICE_PORT", str(settings.service_port))),
        reload=False,
    )
