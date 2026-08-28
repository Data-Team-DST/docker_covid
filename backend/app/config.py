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

    # Modèle — fallback local si MLflow Registry est indisponible (voir ci-dessous)
    model_path: str = "data/models/classification.keras"
    model_version: str = "1.0.0"

    # MLflow Model Registry — chargement prioritaire du modèle taggé mlflow_model_stage.
    # Si vide, indisponible, ou aucun modèle à ce stage : fallback silencieux sur
    # model_path (voir app/models/loader.py). Jamais bloquant au démarrage.
    mlflow_tracking_uri: str = "http://mlflow:5000"
    mlflow_model_name: str = "classification"
    mlflow_model_stage: str = "Production"
    mlflow_lookup_timeout_s: float = 5.0

    # Segmentation Service — génère le mask des images de predict/, qui n'en ont pas
    # contrairement au dataset d'entraînement. Service séparé (U-Net + TensorFlow),
    # appelé en HTTP plutôt qu'embarqué dans le backend
    # (cf. app/features/preprocessing.py).
    segmentation_service_url: str = "http://segmentation-service:8001"
    segmentation_service_timeout_s: float = 10.0

    # Classes — ordre = params.yaml § preprocess.classes (figé par dvc.lock), PAS
    # l'ordre alphabétique. Bug réel trouvé le 2026-08-28 : cette liste était en
    # ordre alphabétique (COVID/Lung_Opacity/Normal/Viral_Pneumonia) alors que
    # l'entraînement utilise COVID=0/Normal=1/Viral Pneumonia=2/Lung_Opacity=3 —
    # seul l'index 0 coïncidait par hasard entre les deux ordres, les index 1-3
    # étaient décalés (Normal→Lung_Opacity, Lung_Opacity→Viral_Pneumonia en sortie
    # de predict.py::predicted_class = class_names[predicted_idx]). Confirmé par un
    # test batch réel (60 images via l'API) : accuracy globale 35% au lieu des 92%
    # de validation loggés sur MLflow pour ce modèle (run legendary-shoat-287).
    class_names: list[str] = [
        "COVID",
        "Normal",
        "Viral_Pneumonia",
        "Lung_Opacity",
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
