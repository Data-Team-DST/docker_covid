"""Configuration centralisée — DS_COVID Backend"""

from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Paramètres de configuration chargés depuis les variables d'environnement."""

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_env: str = "development"
    api_version: str = "0.1.0"

    # Modèle — ADAPTER CE PATH selon le vrai nom du fichier .keras
    model_path: str = "data/models/best_model.keras"
    model_version: str = "1.0.0"

    # Modèle de segmentation pulmonaire (U-Net) — génère le mask des images de predict/,
    # qui n'en ont pas contrairement au dataset d'entraînement. cf. ds_covid.segmentation.
    segmentation_model_path: str = "data/models/lung_unet.keras"

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
    # l'entraînement, section `preprocess` / `segmentation`) sous peine de train/serving skew.
    img_size: tuple[int, int] = (256, 256)
    masking: bool = True
    cropping: bool = True
    clahe: bool = True
    clahe_clip_limit: float = 2.0
    clahe_tile_grid_size: tuple[int, int] = (8, 8)
    denoising_method: Optional[str] = None
    clean_mask_components: int = 2
    clean_mask_closing_kernel: int = 15

    class Config:
        """Configuration Pydantic : source du fichier .env."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Instance globale — importée partout
settings = Settings()
