"""Preprocessing des images — identique à ce qui a été utilisé à l'entraînement"""

import io
import logging

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def preprocess_image(
    image_bytes: bytes, img_size: tuple[int, int] = (224, 224)
) -> np.ndarray:
    """
    Prépare une image brute pour l'inférence.
    Pipeline : bytes → PIL → resize → RGB → normalize [0,1] → batch dim

    Args:
        image_bytes: contenu brut du fichier image
        img_size: taille cible (doit correspondre à l'entraînement)

    Returns:
        np.ndarray de shape (1, H, W, 3), dtype float32, valeurs [0, 1]
    """
    img = Image.open(io.BytesIO(image_bytes))

    # Forcer RGB (les radiographies sont parfois en niveaux de gris ou RGBA)
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Resize
    img = img.resize(img_size, Image.LANCZOS)

    # Normalize
    arr = np.array(img, dtype=np.float32) / 255.0

    # Ajouter dimension batch : (H, W, 3) → (1, H, W, 3)
    return np.expand_dims(arr, axis=0)
