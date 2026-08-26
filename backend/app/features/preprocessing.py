# code-smell: max-lines=200 reason="Pipeline masking/crop/CLAHE dupliqué localement (autonomie du service, cf. frontières de service) + appel HTTP segmentation-service"
"""Preprocessing des images pour l'inférence.

Pipeline autonome (masking + crop poumons + CLAHE + resize + normalisation),
identique à celui de l'entraînement (`deep_learning.preprocessing.apply_pipeline`)
mais dupliqué ici plutôt qu'importé : ce service reste buildable/déployable
indépendamment du pipeline d'entraînement (cf. logging_config.py pour la même
logique appliquée au logging — frontières de service du projet).

Le mask des poumons, lui, est obtenu via un appel HTTP au segmentation-service
(U-Net) plutôt qu'en chargeant le modèle en process : la segmentation reste un
service à part, déployable/scalable indépendamment (cf. `predict_lung_mask`).
"""

import logging
from typing import Optional

import cv2
import httpx
import numpy as np

logger = logging.getLogger(__name__)


def _decode_grayscale(image_bytes: bytes) -> np.ndarray:
    buf = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("Image illisible : format non supporté ou fichier corrompu")
    return img


def squared_crop_to_lungs(masked_img: np.ndarray) -> np.ndarray:
    """
    Rogne l'image masquée pour ne garder que la région contenant les poumons, puis ajoute
    du padding pour obtenir une image carrée (recentre les poumons, réduit le bruit de
    fond, préserve un format carré pour les étapes suivantes du pipeline).

    Raises:
        ValueError - si l'image masquée ne contient aucun pixel non nul
    """
    rows = np.any(masked_img > 0, axis=1)
    cols = np.any(masked_img > 0, axis=0)

    if not rows.any() or not cols.any():
        raise ValueError("L'image masquée ne contient aucun pixel de poumon (tous les pixels sont à zéro)")

    r1, r2 = np.where(rows)[0][[0, -1]]
    c1, c2 = np.where(cols)[0][[0, -1]]

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


def apply_pipeline(
    img_array: np.ndarray,
    mask_array: Optional[np.ndarray],
    cropping: bool,
    denoising_method: Optional[str],
    clahe_processor: Optional[cv2.CLAHE],
    target_size: int,
) -> np.ndarray:
    """Applique masking + crop + CLAHE + resize à une image en niveaux de gris déjà
    chargée en mémoire. Identique à `deep_learning.preprocessing.apply_pipeline`."""

    if denoising_method == "gaussian":
        img_array = cv2.GaussianBlur(img_array, (5, 5), 0)

    if mask_array is not None:
        mask_array = cv2.resize(
            mask_array, (img_array.shape[1], img_array.shape[0]), interpolation=cv2.INTER_NEAREST
        )
        mask_binary = (mask_array * 255).astype(np.uint8) if mask_array.max() <= 1 else mask_array.astype(np.uint8)
        masked_array = cv2.bitwise_and(img_array, img_array, mask=mask_binary)

        if cropping:
            masked_array = squared_crop_to_lungs(masked_array)

        img_array = masked_array

    if clahe_processor:
        img_array = clahe_processor.apply(img_array)

    return cv2.resize(img_array, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4)


def predict_lung_mask(
    image_bytes: bytes,
    segmentation_service_url: str,
    timeout: float,
    client: Optional[httpx.Client] = None,
) -> np.ndarray:
    """Appelle le segmentation-service pour obtenir le mask des poumons.

    Args:
        image_bytes: contenu brut de l'image (n'importe quelle taille/format)
        segmentation_service_url: base URL du segmentation-service (ex: http://segmentation-service:8001)
        timeout: délai max en secondes pour l'appel HTTP
        client: client httpx à utiliser (permet l'injection d'un transport de test) ;
            None = requête réelle via httpx.post

    Returns:
        np.ndarray (H, W) uint8 - mask binaire {0, 255}, mêmes dimensions que l'image envoyée

    Raises:
        httpx.HTTPError - si le service est injoignable ou renvoie une erreur
    """
    files = {"file": ("image.png", image_bytes, "application/octet-stream")}
    url = f"{segmentation_service_url}/v1/segment"
    response = client.post(url, files=files, timeout=timeout) if client else httpx.post(url, files=files, timeout=timeout)
    response.raise_for_status()
    mask = cv2.imdecode(np.frombuffer(response.content, np.uint8), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        raise ValueError("Réponse du segmentation-service illisible")
    return mask


def preprocess_image(
    image_bytes: bytes,
    img_size: tuple[int, int] = (256, 256),
    masking: bool = True,
    cropping: bool = True,
    clahe: bool = True,
    clahe_clip_limit: float = 2.0,
    clahe_tile_grid_size: tuple[int, int] = (8, 8),
    denoising_method: Optional[str] = None,
    segmentation_service_url: str = "",
    segmentation_service_timeout_s: float = 10.0,
    segmentation_client: Optional[httpx.Client] = None,
) -> np.ndarray:
    """
    Prépare une image brute pour l'inférence.

    Pipeline : bytes → grayscale → mask (appel HTTP au segmentation-service) →
    masking+crop poumons → CLAHE → resize → normalize [-1, 1] — identique au
    preprocessing d'entraînement (masking/crop/CLAHE), sauf que le mask est obtenu
    via le segmentation-service plutôt que chargé depuis le dataset (les images de
    predict/ n'ont pas de mask associé).

    Args:
        image_bytes: contenu brut du fichier image
        img_size: taille cible carrée (doit correspondre à params.yaml preprocess.img_size)
        masking: si True, appelle le segmentation-service pour masquer/recadrer l'image
            (désactiver provoque un train/serving skew — à éviter en production)
        cropping / clahe / clahe_clip_limit / clahe_tile_grid_size / denoising_method :
            mêmes options que `params.yaml` (section `preprocess`)
        segmentation_service_url / segmentation_service_timeout_s: cf. `predict_lung_mask`

    Returns:
        np.ndarray de shape (1, H, W, 1), dtype float32, valeurs [-1, 1]

    Raises:
        ValueError - si les bytes ne représentent pas une image décodable
        httpx.HTTPError - si masking=True et le segmentation-service est injoignable
    """
    img_array = _decode_grayscale(image_bytes)

    mask_array = None
    if masking:
        mask_array = predict_lung_mask(
            image_bytes, segmentation_service_url, segmentation_service_timeout_s, client=segmentation_client
        )

    clahe_processor = (
        cv2.createCLAHE(clipLimit=clahe_clip_limit, tileGridSize=tuple(clahe_tile_grid_size)) if clahe else None
    )

    processed = apply_pipeline(
        img_array,
        mask_array,
        cropping=cropping and mask_array is not None,
        denoising_method=denoising_method,
        clahe_processor=clahe_processor,
        target_size=img_size[0],
    )

    arr = (processed.astype("float32") / 127.5) - 1.0
    return arr.reshape(1, img_size[0], img_size[1], 1)
