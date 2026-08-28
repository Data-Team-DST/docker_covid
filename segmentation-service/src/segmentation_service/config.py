"""Configuration centralisée — Segmentation Service"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Paramètres de configuration chargés depuis les variables d'environnement."""

    service_port: int = 8001

    # Modèle — DOIT correspondre à params.yaml (mlflow.segmentation_model_name /
    # entraîné par le stage DVC train_segmentation, cf. trainer/src/ds_covid/segmentation.py)
    # Fallback local si MLflow Registry est indisponible (voir ci-dessous).
    model_path: str = "data/models/segmentation.keras"
    model_version: str = "1.0.0"

    # MLflow Model Registry — chargement prioritaire du modèle taggé mlflow_model_stage.
    # Si vide, indisponible, ou aucun modèle à ce stage : fallback silencieux sur
    # model_path (voir model.py). Jamais bloquant au démarrage.
    mlflow_tracking_uri: str = "http://mlflow:5000"
    mlflow_model_name: str = "segmentation"
    mlflow_model_stage: str = "Production"
    mlflow_lookup_timeout_s: float = 5.0

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
