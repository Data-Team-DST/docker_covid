"""Chargement du modèle Keras — singleton thread-safe"""
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class ModelLoader:
    """Singleton : charge le modèle une fois au démarrage, le garde en mémoire."""

    def __init__(self):
        self._model = None
        self.is_loaded = False

    def load(self, model_path: str = None):
        from app.config import settings
        path = Path(model_path or settings.model_path)

        if not path.exists():
            logger.warning(f"Fichier modèle introuvable : {path}")
            logger.warning("→ Mets ton fichier .keras dans data/models/ et redémarre")
            return

        try:
            import tensorflow as tf
            self._model = tf.keras.models.load_model(str(path))
            self.is_loaded = True
            logger.info(f"Modèle chargé : {path} ({path.stat().st_size / 1e6:.1f} Mo)")
        except Exception as e:
            logger.error(f"Échec chargement modèle : {e}")

    def predict(self, img_array: np.ndarray) -> np.ndarray:
        """Retourne le vecteur de probabilités (shape: [4])."""
        if not self.is_loaded:
            raise RuntimeError("Modèle non chargé")
        preds = self._model.predict(img_array, verbose=0)
        return preds[0]  # shape [4]


# Instance globale importée par les endpoints
model_loader = ModelLoader()
