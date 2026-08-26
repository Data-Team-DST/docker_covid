"""Point d'entrée FastAPI — DS_COVID ML Backend"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.health import router as health_router
from app.api.metrics import router as metrics_router
from app.api.predict import router as predict_router
from app.config import settings
from app.lifespan import lifespan
from app.logging_config import setup_logging
from app.middleware import log_requests
from app.rate_limit import limiter

setup_logging()
logger = logging.getLogger(__name__)


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

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(log_requests)

app.include_router(health_router, tags=["Health"])
app.include_router(predict_router, prefix="/api/v1", tags=["Prediction"])
app.include_router(metrics_router, tags=["Monitoring"])


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "DS_COVID API", "docs": "/docs", "health": "/health"}
