"""DS_COVID — DVC Service : opérations DVC (status/pull/push/repro).

Extrait de data-service (chantier point 16) : data-service reste un service
de lecture (stats, recherche, images), ce service porte les opérations DVC
qui mutent l'état local — séparation des concerns lecture / écriture."""
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dvc_service.api.v1.router import api_router
from dvc_service.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DS_COVID — DVC Service",
    description="Opérations DVC : status/pull/push/repro (subprocess dvc CLI)",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup():
    logger.info("dvc-service starting", extra={"extra": {"port": os.getenv("DVC_SERVICE_PORT", "5003")}})


@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy", "service": "dvc-service", "version": "0.1.0"}


app.include_router(api_router, prefix="/v1")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("DVC_SERVICE_PORT", "5003"))
    uvicorn.run("dvc_service.main:app", host="0.0.0.0", port=port, reload=False)
