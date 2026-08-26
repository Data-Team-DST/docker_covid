"""
U-Net de segmentation pulmonaire (encoder MobileNetV2 pré-entraîné).

Sert à générer le mask des poumons pour les images de predict/ (qui n'ont pas de
mask associé, contrairement au dataset raw), afin de reproduire à l'inférence le
même preprocessing (masking + crop + CLAHE, cf. deep_learning.preprocessing) que celui
appliqué au training set du modèle de classification.
"""

from pathlib import Path
from typing import Tuple

import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras import Model, layers


def build_unet(input_shape: Tuple[int, int, int] = (256, 256, 1)) -> Tuple[tf.keras.Model, tf.keras.Model]:
    """U-Net avec encoder MobileNetV2 pré-entraîné (ImageNet) et decoder + skip connections codés à la main.

    Renvoie (model, encoder) : `encoder` est nécessaire pour geler/dégeler ses layers
    entre la phase 1 (decoder seul) et la phase 2 (fine-tuning complet). Les layers de
    `encoder` sont les mêmes instances que celles utilisées dans le graphe de `model`
    (extraites par tenseurs de sortie, pas appelées comme sous-modèle) : changer leur
    `.trainable` affecte donc directement l'entraînement de `model`.
    """
    inputs = tf.keras.Input(shape=input_shape)

    # MobileNetV2 attend 3 canaux -> on duplique le canal grayscale
    x = layers.Concatenate()([inputs, inputs, inputs])

    encoder = tf.keras.applications.MobileNetV2(input_tensor=x, include_top=False, weights="imagenet")

    skip_names = ["block_1_expand_relu", "block_3_expand_relu", "block_6_expand_relu", "block_13_expand_relu"]
    skips = [encoder.get_layer(n).output for n in skip_names]
    bottleneck = encoder.get_layer("block_16_project").output

    x = bottleneck
    for skip in reversed(skips):
        x = layers.Conv2DTranspose(skip.shape[-1], 3, strides=2, padding="same")(x)
        x = layers.Concatenate()([x, skip])
        x = layers.Conv2D(skip.shape[-1], 3, padding="same", activation="relu")(x)
        x = layers.Conv2D(skip.shape[-1], 3, padding="same", activation="relu")(x)

    outputs = layers.Conv2DTranspose(1, 3, strides=2, padding="same", activation="sigmoid")(x)
    model = Model(inputs, outputs, name="lung_unet")
    return model, encoder


def dice_coef(y_true, y_pred, smooth: float = 1.0):
    y_true_f = tf.reshape(y_true, [-1])
    y_pred_f = tf.reshape(y_pred, [-1])
    intersection = tf.reduce_sum(y_true_f * y_pred_f)
    return (2.0 * intersection + smooth) / (tf.reduce_sum(y_true_f) + tf.reduce_sum(y_pred_f) + smooth)


def dice_loss(y_true, y_pred):
    return 1 - dice_coef(y_true, y_pred)


def combined_loss(y_true, y_pred):
    return tf.keras.losses.binary_crossentropy(y_true, y_pred) + dice_loss(y_true, y_pred)


def iou_metric(y_true, y_pred, smooth: float = 1.0):
    y_true_f = tf.reshape(y_true, [-1])
    y_pred_f = tf.reshape(tf.cast(y_pred > 0.5, tf.float32), [-1])
    intersection = tf.reduce_sum(y_true_f * y_pred_f)
    union = tf.reduce_sum(y_true_f) + tf.reduce_sum(y_pred_f) - intersection
    return (intersection + smooth) / (union + smooth)


def clean_mask(mask: np.ndarray, n_components: int = 2, closing_kernel_size: int = 15) -> np.ndarray:
    """Nettoie un mask prédit : ne garde que les `n_components` plus grandes composantes
    connexes (élimine les îlots parasites) puis comble les petits trous par fermeture
    morphologique.

    Args:
        mask: np.ndarray (H, W) - mask binaire ou en niveaux de gris
        n_components: nombre de composantes connexes à conserver (les plus grandes par aire)
        closing_kernel_size: taille du noyau elliptique utilisé pour la fermeture morphologique

    Returns:
        np.ndarray (H, W) uint8 - mask nettoyé, valeurs {0, 255}
    """
    mask_binary = (mask > 0).astype(np.uint8) * 255

    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask_binary, connectivity=8)
    if n_labels <= 1:
        return mask_binary

    areas = stats[1:, cv2.CC_STAT_AREA]
    n_keep = min(n_components, len(areas))
    keep_labels = np.argsort(areas)[::-1][:n_keep] + 1

    cleaned = np.isin(labels, keep_labels).astype(np.uint8) * 255

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (closing_kernel_size, closing_kernel_size))
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)

    return cleaned


def collect_pairs(split_dir: Path, classes: dict) -> Tuple[list[Path], list[Path]]:
    """Liste tous les couples (image, mask) disponibles sous `split_dir`, toutes classes
    confondues (la segmentation - silhouette des poumons - est indépendante du label
    pathologique de l'image, cf. `classes` utilisé uniquement pour parcourir les dossiers).

    Returns:
        (img_paths, mask_paths) - listes alignées de même longueur
    """
    img_paths, mask_paths = [], []
    for class_name in classes:
        images_dir = split_dir / class_name / "images"
        masks_dir = split_dir / class_name / "masks"
        if not images_dir.exists():
            continue
        for img_path in sorted(images_dir.glob("*.png")):
            mask_path = masks_dir / img_path.name
            if mask_path.exists():
                img_paths.append(img_path)
                mask_paths.append(mask_path)
    return img_paths, mask_paths


def load_pair(img_path: Path, mask_path: Path, img_size: int) -> Tuple[np.ndarray, np.ndarray]:
    """Charge et redimensionne une paire (image, mask) pour l'entraînement du U-Net.

    L'image est en niveaux de gris, normalisée dans [0, 1]. Le mask est redimensionné
    en INTER_NEAREST (pour rester binaire) puis seuillé à {0, 1}.
    """
    img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Impossible de charger l'image: {img_path}")
    img = cv2.resize(img, (img_size, img_size), interpolation=cv2.INTER_LINEAR)
    img = (img.astype("float32") / 255.0).reshape(img_size, img_size, 1)

    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        raise FileNotFoundError(f"Impossible de charger le mask: {mask_path}")
    mask = cv2.resize(mask, (img_size, img_size), interpolation=cv2.INTER_NEAREST)
    mask = (mask > 127).astype("float32").reshape(img_size, img_size, 1)

    return img, mask
