"""
Image preprocessing pipeline for COVID-19 radiography images.

Notes de développement :

Numpy : Image (H, W) i.e (lignes, colonnes)
cv2 : Image (W, H)

Différence entre np.array et np.ndarray : np.array est une fonction pour créer un ndarray, mais le type réel est np.ndarray.
Donc on peut annoter les fonctions avec np.ndarray pour plus de clarté.
"""

from pathlib import Path
from typing import Optional

import cv2
import numpy as np


def squared_crop_to_lungs(masked_img: np.ndarray) -> np.ndarray:
    """
    Rogne l'image masquée pour ne garder que la région contenant les poumons, puis ajoute du padding pour obtenir une image carrée.
    Cela permet de recentrer les poumons et de réduire le bruit de fond, tout en préservant un format carré pour les étapes suivantes du pipeline.

    Args:
         masked_img: np.ndarray (H, W) - image après masquage, avec des pixels de poumon > 0 et le reste à 0

    Returns:
         np.ndarray - image rognée et paddée pour être carrée, centrée sur les poumons

    Raises:
         ValueError - si l'image masquée ne contient aucun pixel non nul
    """

    # On ne garde que les pixels de poumon (i.e non noirs)

    rows = np.any(masked_img > 0, axis=1)  # lignes contenant au moins un pixel > 0
    cols = np.any(masked_img > 0, axis=0)  # colonnes contenant au moins un pixel > 0

    if not rows.any() or not cols.any():
        raise ValueError("L'image masquée ne contient aucun pixel de poumon (tous les pixels sont à zéro)")

    r1, r2 = np.where(rows)[0][[0, -1]]  # indices de la première et dernière ligne contenant du poumon
    c1, c2 = np.where(cols)[0][[0, -1]]  # indices de la première et dernière colonne contenant du poumon

    h, w = r2 - r1 + 1, c2 - c1 + 1
    side = max(h, w)
    cy, cx = (r1 + r2) // 2, (c1 + c2) // 2

    y1 = max(0, cy - side // 2)
    x1 = max(0, cx - side // 2)
    y2 = min(masked_img.shape[0], y1 + side)
    x2 = min(masked_img.shape[1], x1 + side)

    # Si x2 ou y2 a été clampé, on réajuste x1 et y1 pour garder un carré de la bonne taille
    y1, x1 = max(0, y2 - side), max(0, x2 - side)

    return masked_img[y1:y2, x1:x2]


def process_single_image(
    img_path: Path,
    mask_path: Optional[Path],  # if None we skip masking
    cropping: bool,
    denoising_method: Optional[str],  # if None we skip denoising
    clahe_processor: Optional[cv2.CLAHE],  # if None we skip CLAHE
    target_size: int,
) -> np.ndarray:
    """
    Applique le pipeline de prétraitement à une seule image, selon les options choisies.

    ** On ne manipule que des images en L (grayscale) car ce sont des radiographies. **

    Pipeline complet détaillé :

    1) chargement des raw data : l'image (299x299) et son Mask (256x256)

    1) a) [OPTIONNEL] Denoising avec une méthode comme Gaussian Blur, si jamais la qualité des images est mauvaise
    (pas notre cas, curated dataset, mais pourrait être le cas d'une image donnée dans predict/)

    2) Resize du Mask vers (299x299) pour fitter image. On utilise une interpolation de type INTER_NEAREST pour ne pas créer des valeurs autres que 0 ou 1

    3) Masking (multiplication pixel par pixel)

    4) Crop (rogner l'image masquée) puis padding pour retrouver une image carrée

    5) CLAHE pour améliorer contraste local de l'image

    6) Resize final vers le target size (ex : 128x128 ou 256x256) avec interpolation de type LANCZOS4 pour préserver les détails

    Args:
         img_path: Path - chemin vers l'image à traiter
         mask_path: Path | None - chemin vers le mask correspondant, ou None pour ne pas faire de masking
         cropping: bool - appliquer le crop+padding pour recentrer les poumons si True (seulement actif si mask_path n'est pas None)
         denoising_method: str | None - méthode de denoising à appliquer (ex: 'gaussian') ou None pour aucune
         clahe_processor: cv2.CLAHE | None - instance de cv2.CLAHE à appliquer, ou None pour ne pas faire de CLAHE
         target_size: int - résolution cible (carrée) pour l'image finale (ex: 128, 256)

    Returns:
         np.ndarray - image traitée au format numpy array, prête à être sauvegardée

    Raises:
         FileNotFoundError - si l'image ou le mask (si masking activé) ne peuvent pas être chargés
         ValueError - si le crop est activé mais que l'image masquée ne contient aucun pixel de poumon (tous les pixels sont à zéro)
    """

    # Charger l'image
    img_array = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if img_array is None:
        raise FileNotFoundError(f"Impossible de charger l'image: {img_path}")

    # Denoising (optionnel)
    if denoising_method == "gaussian":
        img_array = cv2.GaussianBlur(img_array, (5, 5), 0)

    # Masking, cropping, padding (optionnel)
    if mask_path:
        mask_array = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask_array is None:
            raise FileNotFoundError(f"Impossible de charger le mask: {mask_path}")

        # Redimensionner le mask à la taille de l'image avec interpolation nearest pour garder les valeurs binaires
        mask_array = cv2.resize(
            mask_array, (img_array.shape[1], img_array.shape[0]), interpolation=cv2.INTER_NEAREST
        )

        # Préparer le mask pour OpenCV (0/255 requis)
        if mask_array.max() <= 1:  # Should not be the case with our images, but just in case
            mask_binary = (mask_array * 255).astype(np.uint8)
        else:
            mask_binary = mask_array.astype(np.uint8)

        # Appliquer le masquage avec bitwise_and
        masked_array = cv2.bitwise_and(img_array, img_array, mask=mask_binary)

        # Optionnel : recadrage + padding pour recentrer les poumons
        if cropping:
            masked_array = squared_crop_to_lungs(masked_array)

        img_array = masked_array

    # CLAHE (optionnel)
    if clahe_processor:
        img_array = clahe_processor.apply(img_array)

    # Redimensionner (cv2) avec LANCZOS4 pour préserver les détails
    img_array = cv2.resize(img_array, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4)

    return img_array  # uint8 (H, W)
