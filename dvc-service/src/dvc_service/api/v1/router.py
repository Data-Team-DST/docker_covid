"""Router v1 — DS_COVID DVC Service (opérations DVC : status/pull/push/repro).

Extrait de data-service (chantier point 16) : data-service reste lecture
seule (stats, recherche, images), ce service porte les opérations DVC qui
mutent l'état local (potentiellement longues — dvc repro jusqu'à 5 min)."""
import logging
import os

import requests
from fastapi import APIRouter, HTTPException

from dvc_service.dvc_runner import run_dvc

logger = logging.getLogger(__name__)
api_router = APIRouter()

DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://data-service:5001")


def _invalidate_data_service_cache() -> None:
    """Best-effort : force data-service à re-scanner data/ après un pull qui a
    changé les fichiers sur disque (le hash .dvc, lui, ne change pas — cf.
    commit history). N'échoue jamais la réponse de /pull si data-service est
    indisponible (R8 : communication HTTP entre services, jamais de partage
    de filesystem/état)."""
    try:
        requests.get(f"{DATA_SERVICE_URL}/v1/data/stats", params={"refresh": "true"}, timeout=10)
    except requests.exceptions.RequestException as e:
        logger.warning("Invalidation cache data-service échouée (ignorée) : %s", e)


@api_router.get("/dvc/status", tags=["dvc"])
def dvc_status():
    return run_dvc(["status"])


@api_router.get("/dvc/remotes", tags=["dvc"])
def dvc_remotes():
    return run_dvc(["remote", "list"])


@api_router.post("/dvc/pull", tags=["dvc"])
def dvc_pull(target: str | None = None):
    cmd = ["pull"]
    if target:
        cmd.append(target)
    result = run_dvc(cmd)
    if not result["success"]:
        stderr = result["stderr"] or ""
        if "Missing cache files" in stderr or "not in cache" in stderr:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Données absentes du remote MinIO — "
                    "faire dvc push depuis une machine avec data/raw/ complet"
                ),
            )
        raise HTTPException(
            status_code=500, detail=stderr or "dvc pull échoué"
        )
    _invalidate_data_service_cache()
    return result


@api_router.post("/dvc/push", tags=["dvc"])
def dvc_push(target: str | None = None):
    cmd = ["push"]
    if target:
        cmd.append(target)
    result = run_dvc(cmd)
    if not result["success"]:
        raise HTTPException(
            status_code=500, detail=result["stderr"] or "dvc push échoué"
        )
    return result


@api_router.post("/dvc/repro", tags=["dvc"])
def dvc_repro():
    result = run_dvc(["repro"])
    if not result["success"]:
        raise HTTPException(
            status_code=500, detail=result["stderr"] or "dvc repro échoué"
        )
    _invalidate_data_service_cache()
    return result
