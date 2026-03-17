"""Configuration centralisée — DS_COVID Backend"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_env: str = "development"
    api_version: str = "0.1.0"

    # Modèle — ADAPTER CE PATH selon le vrai nom du fichier .keras
    model_path: str = "data/models/best_model.keras"
    model_version: str = "1.0.0"

    # Classes (ordre doit correspondre à l'entraînement)
    class_names: list[str] = ["COVID", "Lung_Opacity", "Normal", "Viral_Pneumonia"]

    # Image preprocessing
    img_size: tuple[int, int] = (224, 224)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Instance globale — importée partout
settings = Settings()
