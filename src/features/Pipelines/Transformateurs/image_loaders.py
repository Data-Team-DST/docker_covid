"""Image loading transformers - Simplified version."""

from pathlib import Path
from typing import List, Union
from PIL import Image
from sklearn.base import BaseEstimator, TransformerMixin


class ImageLoader(BaseEstimator, TransformerMixin):
    """
    Charge des images depuis des chemins de fichiers.
    
    Simplifié: juste charger les images en grayscale ou RGB, sans complexité.
    
    Parameters
    ----------
    color_mode : str, default='L'
        'L' pour grayscale, 'RGB' pour couleur
    """

    def __init__(self, color_mode='L'):
        self.color_mode = color_mode

    def fit(self, X, y=None):
        """Pas d'apprentissage nécessaire."""
        return self

    def transform(self, X: List[Union[str, Path]]):
        """Charge les images depuis les chemins."""
        images = []
        for path in X:
            img = Image.open(path).convert(self.color_mode)
            images.append(img)
        return images
