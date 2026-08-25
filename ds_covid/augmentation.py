"""
Data augmentation pour paires image/mask de radiographies.

Les transformations géométriques (flip, rotation, zoom) sont appliquées
identiquement à l'image et à son mask pour garder l'alignement pixel-à-pixel
(le mask est interpolé en INTER_NEAREST pour rester binaire). La luminosité
n'affecte que l'image.
"""

from typing import Optional, Tuple

import cv2
import numpy as np


def _rotate(img: np.ndarray, angle: float, interpolation: int) -> np.ndarray:
    h, w = img.shape[:2]
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, matrix, (w, h), flags=interpolation, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def _zoom(img: np.ndarray, factor: float, interpolation: int) -> np.ndarray:
    h, w = img.shape[:2]
    new_h, new_w = max(1, round(h * factor)), max(1, round(w * factor))
    resized = cv2.resize(img, (new_w, new_h), interpolation=interpolation)

    if factor >= 1.0:
        y1, x1 = (new_h - h) // 2, (new_w - w) // 2
        return resized[y1 : y1 + h, x1 : x1 + w]

    pad_h, pad_w = h - new_h, w - new_w
    top, bottom = pad_h // 2, pad_h - pad_h // 2
    left, right = pad_w // 2, pad_w - pad_w // 2
    return cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=0)


def _adjust_brightness(img: np.ndarray, factor: float) -> np.ndarray:
    return np.clip(img.astype(np.float32) * factor, 0, 255).astype(np.uint8)


def augment_pair(
    img: np.ndarray,
    mask: Optional[np.ndarray],
    rng: np.random.Generator,
    rotation_range: float = 15.0,
    zoom_range: Tuple[float, float] = (0.9, 1.1),
    brightness_range: Tuple[float, float] = (0.8, 1.2),
    flip_horizontal: bool = True,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Applique une combinaison aléatoire de flip/rotation/zoom/luminosité à une paire image+mask.

    Args:
        img: np.ndarray (H, W) uint8 - image en niveaux de gris
        mask: np.ndarray (H, W) uint8 | None - mask binaire correspondant, ou None
        rng: np.random.Generator - générateur seedé pour la reproductibilité
        rotation_range: amplitude max de rotation en degrés (0 pour désactiver)
        zoom_range: (min, max) facteur de zoom, 1.0 = pas de zoom
        brightness_range: (min, max) facteur multiplicatif de luminosité, 1.0 = inchangé
        flip_horizontal: applique un flip horizontal avec 50% de chance si True
            (pas de flip vertical : anatomiquement invalide pour une radiographie thoracique)

    Returns:
        (img_aug, mask_aug) - paire augmentée, mask_aug est None si mask était None
    """
    img_aug = img.copy()
    mask_aug = mask.copy() if mask is not None else None

    if flip_horizontal and rng.random() < 0.5:
        img_aug = cv2.flip(img_aug, 1)
        if mask_aug is not None:
            mask_aug = cv2.flip(mask_aug, 1)

    if rotation_range:
        angle = rng.uniform(-rotation_range, rotation_range)
        img_aug = _rotate(img_aug, angle, cv2.INTER_LINEAR)
        if mask_aug is not None:
            mask_aug = _rotate(mask_aug, angle, cv2.INTER_NEAREST)

    if zoom_range and zoom_range != (1.0, 1.0):
        factor = rng.uniform(*zoom_range)
        img_aug = _zoom(img_aug, factor, cv2.INTER_LINEAR)
        if mask_aug is not None:
            mask_aug = _zoom(mask_aug, factor, cv2.INTER_NEAREST)

    if brightness_range and brightness_range != (1.0, 1.0):
        factor = rng.uniform(*brightness_range)
        img_aug = _adjust_brightness(img_aug, factor)

    return img_aug, mask_aug
