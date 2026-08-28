"""Chargement du modèle Keras — singleton thread-safe.

Priorité MLflow Model Registry (stage Production) ; si indisponible (MLflow down, pas
de modèle à ce stage, timeout...), fallback silencieux sur le fichier .keras local — le
backend démarre dans tous les cas, jamais bloqué par une dépendance réseau.
"""

import logging
import os
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class ModelLoader:
    """Singleton : charge le modèle une fois au démarrage, le garde en mémoire."""

    def __init__(self):
        self._model = None
        self.is_loaded = False
        self.source: str | None = None  # "registry" ou "local", pour observabilité

    def load(self, model_path: str = None):
        """Charge le modèle : MLflow Registry en priorité, fallback fichier local."""
        from app.config import settings

        if self._load_from_registry(settings):
            return
        self._load_from_local_file(model_path, settings)

    def _load_from_registry(self, settings) -> bool:
        """Tente MLflow Model Registry. Ne laisse jamais remonter d'exception — retourne
        False si indisponible, le caller retombe alors sur le fichier local."""
        if not settings.mlflow_tracking_uri:
            return False
        try:
            os.environ.setdefault(
                "MLFLOW_HTTP_REQUEST_TIMEOUT",
                str(int(settings.mlflow_lookup_timeout_s)),
            )
            import mlflow

            mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
            uri = f"models:/{settings.mlflow_model_name}/{settings.mlflow_model_stage}"
            self._model = mlflow.keras.load_model(uri)
            self.is_loaded = True
            self.source = "registry"
            logger.info("Modèle chargé depuis MLflow Registry : %s", uri)
            return True
        except Exception as e:
            logger.warning(
                "MLflow Registry indisponible ou pas de modèle '%s' en stage '%s' (%s) "
                "— fallback sur le fichier local",
                settings.mlflow_model_name,
                settings.mlflow_model_stage,
                e,
            )
            return False

    def _load_from_local_file(self, model_path: str, settings) -> None:
        """Charge le modèle depuis un fichier .keras local (fallback, ou si MLflow n'est
        pas configuré)."""
        path = Path(model_path or settings.model_path)

        if not path.exists():
            logger.warning("Fichier modèle introuvable : %s", path)
            logger.warning("→ Mets ton fichier .keras dans data/models/ et redémarre")
            return

        try:
            import tensorflow as tf

            self._model = tf.keras.models.load_model(str(path))
            self.is_loaded = True
            self.source = "local"
            logger.info(
                "Modèle chargé : %s (%.1f Mo)",
                path,
                path.stat().st_size / 1e6,
            )
        except Exception as e:
            logger.error("Échec chargement modèle : %s", e)

    def predict(self, img_array: np.ndarray) -> np.ndarray:
        """Retourne le vecteur de probabilités (shape [4]) pour le premier (et unique)
        élément du batch."""
        if not self.is_loaded:
            raise RuntimeError("Modèle non chargé")
        preds = self._model.predict(img_array, verbose=0)
        return preds[0]


# Instance globale importée par les endpoints
model_loader = ModelLoader()
