"""DS_COVID — Data Service : gestion DVC et stats données."""
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from data_service.api.v1.router import api_router
from data_service.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DS_COVID — Data Service",
    description="Gestion DVC : pull/push/status + stats données (raw, processed, models)",
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
    logger.info("data-service starting", extra={"extra": {"port": os.getenv("DATA_SERVICE_PORT", "5001")}})


@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy", "service": "data-service", "version": "0.1.0"}


app.include_router(api_router, prefix="/v1")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("DATA_SERVICE_PORT", "5001"))
    uvicorn.run("data_service.main:app", host="0.0.0.0", port=port, reload=False)
