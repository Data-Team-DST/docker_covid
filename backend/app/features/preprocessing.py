"""Preprocessing des images pour l'inférence.

Réutilise le pipeline de `ds_covid.preprocessing` (identique à l'entraînement, cf.
`trainer/src/ds_covid/preprocessing.py` et `trainer/scripts/preprocess.py`) plutôt que d'en
dupliquer un second : masking (via un mask prédit par le U-Net, cf. `predict_lung_mask`)
+ crop poumons + CLAHE + resize + normalisation, sur une image en niveaux de gris.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Protocol

import cv2
import numpy as np

# En image Docker, trainer/src est copié à côté de app/ (cf. backend/Dockerfile,
# COPY trainer/src ./src) : backend/app/features/../../.. -> /app, /src est un sibling.
# En local (pytest/make test-be, hors Docker), ce sibling n'existe pas : on retombe sur
# trainer/src directement, sibling de backend/ à la racine du repo.
_DOCKER_SRC = Path(__file__).resolve().parent.parent.parent / "src"
_LOCAL_TRAINER_SRC = Path(__file__).resolve().parents[3] / "trainer" / "src"
_SRC_DIR = _DOCKER_SRC if (_DOCKER_SRC / "ds_covid").is_dir() else _LOCAL_TRAINER_SRC
sys.path.insert(0, str(_SRC_DIR))

from ds_covid.preprocessing import apply_pipeline  # noqa: E402
from ds_covid.segmentation import clean_mask  # noqa: E402

logger = logging.getLogger(__name__)


class MaskPredictor(Protocol):
    """Interface minimale attendue pour le modèle de segmentation : un `.predict()` qui
    prend un batch (1, H, W, 1) et renvoie directement le premier élément du batch, sans
    dimension de batch (contrat de `app.models.loader.ModelLoader.predict`)."""

    def predict(self, img_array: np.ndarray) -> np.ndarray: ...


def _decode_grayscale(image_bytes: bytes) -> np.ndarray:
    buf = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("Image illisible : format non supporté ou fichier corrompu")
    return img


def predict_lung_mask(
    img_array: np.ndarray,
    segmentation_model: MaskPredictor,
    model_img_size: int,
    clean_components: int,
    clean_kernel: int,
) -> np.ndarray:
    """Prédit le mask des poumons via le U-Net, redimensionné à la taille de `img_array`.

    Args:
        img_array: np.ndarray (H, W) uint8 - image en niveaux de gris, taille originale
        segmentation_model: modèle de segmentation (sortie sigmoid), cf. `MaskPredictor`
        model_img_size: taille (carrée) attendue en entrée du U-Net
        clean_components / clean_kernel: cf. ds_covid.segmentation.clean_mask

    Returns:
        np.ndarray (H, W) uint8 - mask binaire {0, 255} à la taille de l'image d'origine
    """
    resized = cv2.resize(img_array, (model_img_size, model_img_size), interpolation=cv2.INTER_LINEAR)
    x = (resized.astype("float32") / 255.0).reshape(1, model_img_size, model_img_size, 1)

    pred = segmentation_model.predict(x)[:, :, 0]
    mask = (pred > 0.5).astype(np.uint8) * 255
    mask = clean_mask(mask, n_components=clean_components, closing_kernel_size=clean_kernel)

    return cv2.resize(mask, (img_array.shape[1], img_array.shape[0]), interpolation=cv2.INTER_NEAREST)


def preprocess_image(
    image_bytes: bytes,
    img_size: tuple[int, int] = (256, 256),
    segmentation_model: Optional[MaskPredictor] = None,
    masking: bool = True,
    cropping: bool = True,
    clahe: bool = True,
    clahe_clip_limit: float = 2.0,
    clahe_tile_grid_size: tuple[int, int] = (8, 8),
    denoising_method: Optional[str] = None,
    clean_mask_components: int = 2,
    clean_mask_closing_kernel: int = 15,
) -> np.ndarray:
    """
    Prépare une image brute pour l'inférence.

    Pipeline : bytes → grayscale → mask (U-Net) → masking+crop poumons → CLAHE → resize
    → normalize [-1, 1] — identique à `ds_covid.preprocessing.process_single_image`
    (utilisé à l'entraînement), sauf que le mask est prédit ici plutôt que chargé depuis
    le dataset (les images de predict/ n'ont pas de mask associé).

    Args:
        image_bytes: contenu brut du fichier image
        img_size: taille cible carrée (doit correspondre à params.yaml preprocess.img_size)
        segmentation_model: modèle de segmentation pour générer le mask, ou None pour
            désactiver le masking (l'image ne sera alors ni recadrée ni masquée — à
            éviter en production : cf. `masking`, provoque un train/serving skew)
        masking / cropping / clahe / clahe_clip_limit / clahe_tile_grid_size /
            denoising_method / clean_mask_components / clean_mask_closing_kernel :
            mêmes options que `params.yaml` (sections `preprocess` et `segmentation`)

    Returns:
        np.ndarray de shape (1, H, W, 1), dtype float32, valeurs [-1, 1]

    Raises:
        ValueError - si les bytes ne représentent pas une image décodable
    """
    img_array = _decode_grayscale(image_bytes)

    mask_array = None
    if masking and segmentation_model is not None:
        mask_array = predict_lung_mask(
            img_array, segmentation_model, img_size[0], clean_mask_components, clean_mask_closing_kernel
        )
    elif masking:
        logger.warning("Masking activé mais aucun modèle de segmentation fourni — image non masquée")

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
