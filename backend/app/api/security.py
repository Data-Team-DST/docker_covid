"""Sécurité API — authentification par clé X-API-Key (Phase 3)."""

from fastapi import Header, HTTPException, status

from app.config import settings


def verify_api_key(x_api_key: str = Header(default="")) -> None:
    """Vérifie le header X-API-Key si api_key est configuré.

    En mode dev (api_key vide dans .env), l'accès est libre.
    En mode prod, la clé doit correspondre à settings.api_key.

    Raises:
        HTTPException 401 si la clé est invalide.
    """
    if not settings.api_key:
        return  # dev mode — pas de clé configurée
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API invalide ou manquante (header X-API-Key requis).",
        )
