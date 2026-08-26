"""Configuration centralisée — Segmentation Service"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Paramètres de configuration chargés depuis les variables d'environnement."""

    service_port: int = 8001

    # Modèle — DOIT correspondre à params.yaml (mlflow.segmentation_model_name /
    # entraîné par le stage DVC train_segmentation, cf. trainer/deep_learning/segmentation.py)
    model_path: str = "data/models/lung_unet.keras"
    model_version: str = "1.0.0"

    # Résolution attendue en entrée du U-Net — doit correspondre à params.yaml
    # preprocess.img_size (le pipeline d'entraînement est carré).
    img_size: int = 256

    # Post-traitement du mask prédit — cf. params.yaml segmentation.clean_mask_*
    clean_mask_components: int = 2
    clean_mask_closing_kernel: int = 15

    class Config:
        """Configuration Pydantic : source du fichier .env."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Instance globale — importée partout
settings = Settings()
