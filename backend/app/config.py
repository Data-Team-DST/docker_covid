"""Configuration centralisée — DS_COVID Backend"""


from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Paramètres de configuration chargés depuis les variables d'environnement."""

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_env: str = "development"
    api_version: str = "0.1.0"

    # Modèle — ADAPTER CE PATH selon le vrai nom du fichier .keras
    model_path: str = "data/models/classification.keras"
    model_version: str = "1.0.0"

    # Segmentation Service — génère le mask des images de predict/, qui n'en ont pas
    # contrairement au dataset d'entraînement. Service séparé (U-Net + TensorFlow),
    # appelé en HTTP plutôt qu'embarqué dans le backend
    # (cf. app/features/preprocessing.py).
    segmentation_service_url: str = "http://segmentation-service:8001"
    segmentation_service_timeout_s: float = 10.0

    # Classes (ordre doit correspondre à l'entraînement)
    class_names: list[str] = [
        "COVID",
        "Lung_Opacity",
        "Normal",
        "Viral_Pneumonia",
    ]

    # Sécurité (Phase 3) — vide = mode dev sans restriction
    api_key: str = ""
    rate_limit_per_minute: int = 100
    max_upload_size_mb: int = 10

    # Image preprocessing — DOIT correspondre à params.yaml (paramètres utilisés à
    # l'entraînement, section `preprocess` / `segmentation`) sous peine de
    # train/serving skew.
    img_size: tuple[int, int] = (256, 256)
    masking: bool = True
    cropping: bool = True
    clahe: bool = True
    clahe_clip_limit: float = 2.0
    clahe_tile_grid_size: tuple[int, int] = (8, 8)
    denoising_method: str | None = None

    class Config:
        """Configuration Pydantic : source du fichier .env."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @model_validator(mode="after")
    def _require_api_key_in_production(self) -> "Settings":
        """Fail-fast : refuse de démarrer en prod sans clé API (pas de fail-open
        silencieux)."""
        if self.api_env == "production" and not self.api_key:
            raise ValueError(
                "API_KEY ne peut pas être vide quand API_ENV=production "
                "(l'authentification serait désactivée sur /api/v1/predict)."
            )
        return self


# Instance globale — importée partout
settings = Settings()
