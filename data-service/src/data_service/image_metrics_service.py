"""Métriques d'image et échantillonnage par classe — logique portée depuis
frontend/page/02_donnees/_data_utils.py (chantier point 15, migration vers dashboard).
"""

import random
from pathlib import Path

import numpy as np
from PIL import Image

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}


def compute_image_metrics(img: Image.Image) -> dict:
    """Calcule luminosité moyenne, contraste (écart-type) et entropie de Shannon."""
    arr = np.array(img.convert("RGB"), dtype=np.float32)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    l_channel = 0.299 * r + 0.587 * g + 0.114 * b
    mean_lum = float(np.mean(l_channel))
    std_lum = float(np.std(l_channel))
    hist, _ = np.histogram(l_channel.flatten(), bins=256, range=(0, 255))
    probs = hist / (hist.sum() + 1e-12)
    probs = probs[probs > 0]
    entropy = float(-(probs * np.log2(probs)).sum()) if probs.size > 0 else 0.0
    return {
        "luminosity_mean": mean_lum,
        "contrast_std": std_lum,
        "entropy": entropy,
    }


def mask_coverage(mask_path: Path) -> float | None:
    """Retourne le pourcentage de pixels non-nuls d'un masque binaire."""
    if not mask_path.exists():
        return None
    try:
        m = Image.open(mask_path).convert("L")
        arr = np.array(m)
        total = arr.size
        return 100.0 * np.count_nonzero(arr) / total if total > 0 else 0.0
    except OSError:
        return None


def sample_images_from_class(root: Path, cls: str, n: int) -> list[Path]:
    """Retourne jusqu'à n chemins d'images tirés aléatoirement dans une classe."""
    images_dir = root / cls / "images"
    if not images_dir.exists():
        return []
    imgs = sorted(
        p for p in images_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    )
    if len(imgs) <= n:
        return imgs
    return random.Random().sample(imgs, k=n)
