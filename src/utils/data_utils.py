"""
Data loading and preprocessing utilities for Jupyter notebooks.

This module provides functions for:
- Loading datasets
- Creating preprocessing pipelines
- Train/val/test splitting
- Class weight computation
- Data augmentation generators

Author: Data Pipeline Team
Date: November 2025
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import keras
import numpy as np
from keras.applications.efficientnet import preprocess_input as effnet_preprocess
from keras.applications.inception_v3 import preprocess_input as inception_preprocess
from keras.applications.resnet50 import preprocess_input as resnet_preprocess
from keras.applications.vgg16 import preprocess_input as vgg16_preprocess
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.utils.class_weight import compute_class_weight

# ImageDataGenerator is deprecated in Keras 3, use tf.keras version
# pylint: disable=import-error,no-name-in-module
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# Import des transformateurs V3
from src.features.St_Pipeline.Transformateurs import (
    ImagePathLoader,
    ImageResizer,
    ImageMasker,
)

# Configure logger
logger = logging.getLogger(__name__)


# pylint: disable=too-many-locals
def load_dataset(
    data_dir: Path,
    categories: List[str],
    n_images_per_class: Optional[int] = None,
    load_masks: bool = False,
    verbose: bool = True,
) -> Tuple[List[Path], List[Path], List[str], np.ndarray]:
    """
    Load image paths and labels from dataset directory.

    Args:
        data_dir: Root directory of the dataset
        categories: List of category names
        n_images_per_class: Maximum number of images per class (None = all)
        load_masks: If True, also load mask paths
        verbose: Print loading information

    Returns:
        Tuple of (image_paths, mask_paths, labels, labels_int)
        If load_masks=False, mask_paths will be empty list
    """
    if verbose:
        print("=" * 70)
        print("CHARGEMENT DES DONNÉES")
        print("=" * 70)

    image_paths = []
    mask_paths = []
    labels = []
    labels_int = []

    for idx, cat in enumerate(categories):
        cat_path = data_dir / cat / "images"

        if not cat_path.exists():
            logger.warning("Category path not found: %s", cat_path)
            continue

        imgs = sorted(list(cat_path.glob("*.png")))

        if n_images_per_class:
            imgs = imgs[:n_images_per_class]

        if load_masks:
            # Load corresponding masks
            mask_cat_path = data_dir / cat / "masks"
            for img_path in imgs:
                mask_path = mask_cat_path / img_path.name
                if mask_path.exists():
                    image_paths.append(img_path)
                    mask_paths.append(mask_path)
                    labels.append(cat)
                    labels_int.append(idx)
        else:
            # Load only images
            image_paths.extend(imgs)
            labels.extend([cat] * len(imgs))
            labels_int.extend([idx] * len(imgs))

        if verbose:
            suffix = " (avec masques)" if load_masks else ""
            print(f"  {cat:20s}: {len(imgs):4d} images{suffix}")

    labels_int = np.array(labels_int)

    if verbose:
        print(f"\n  Total: {len(image_paths)} images")
        print(f"  Classes: {len(categories)}")
        print(f"  Distribution: {np.bincount(labels_int)}")
        if load_masks:
            print(f"\n✅ Chemins des masques récupérés: {len(mask_paths)}")

    return image_paths, mask_paths, labels, labels_int


def create_preprocessing_pipeline(
    img_size: Tuple[int, int] = (128, 128),
    color_mode: str = "RGB",
    mask_paths: Optional[List[Path]] = None,
    verbose: bool = True,
) -> Pipeline:
    """
    Create a preprocessing pipeline for images.

    Args:
        img_size: Target image size (width, height)
        color_mode: 'RGB' or 'L' (grayscale)
        mask_paths: Optional mask paths for ImageMasker
        verbose: Print pipeline information

    Returns:
        sklearn Pipeline
    """
    if verbose:
        print("=" * 70)
        print("PREPROCESSING PIPELINE")
        print("=" * 70)

    # NOTE: Cette fonction est dépréciée - utiliser les nouveaux transformateurs V3 à la place
    # Voir: src.features.St_Pipeline.Transformateurs
    
    raise DeprecationWarning(
        "create_preprocessing_pipeline() est obsolète. "
        "Utilisez les transformateurs V3 dans src.features.St_Pipeline.Transformateurs:\n"
        "  Pipeline([\n"
        "    ('loader', ImagePathLoader(root_dir=...)),\n"
        "    ('resizer', ImageResizer(img_size=...)),\n"
        "    ('normalizer', ImageNormalizer()),\n"
        "  ])"
    )

    if verbose:
        print(f"\n✅ Pipeline créée avec {len(steps)} étapes")

    return pipeline


# pylint: disable=too-many-arguments,too-many-positional-arguments
def prepare_train_val_test_split(
    images: np.ndarray,
    labels_int: np.ndarray,
    num_classes: int,
    test_size: float = 0.15,
    val_size: float = 0.15,
    random_seed: int = 42,
    verbose: bool = True,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Split data into train/validation/test sets with one-hot encoding.

    Args:
        images: Array of images
        labels_int: Integer labels
        num_classes: Number of classes
        test_size: Proportion of test set
        val_size: Proportion of validation set (from total)
        random_seed: Random seed for reproducibility
        verbose: Print split information

    Returns:
        Tuple of (x_train, x_val, x_test, y_train_cat, y_val_cat, y_test_cat)
    """
    if verbose:
        print("=" * 70)
        print("TRAIN/VALIDATION/TEST SPLIT")
        print("=" * 70)

    # Validate input consistency
    if len(images) != len(labels_int):
        error_msg = (
            f"⚠️  ERREUR: Nombre d'images ({len(images)}) != nombre de labels ({len(labels_int)})\n"
            f"   Différence: {abs(len(images) - len(labels_int))} échantillon(s)\n"
        )
        print(error_msg)

    # First split: train+val vs test
    x_train_val, x_test, y_train_val, y_test = train_test_split(
        images,
        labels_int,
        test_size=test_size,
        random_state=random_seed,
        stratify=labels_int,
    )

    # Second split: train vs val
    val_size_adjusted = val_size / (1 - test_size)
    x_train, x_val, y_train, y_val = train_test_split(
        x_train_val,
        y_train_val,
        test_size=val_size_adjusted,
        random_state=random_seed,
        stratify=y_train_val,
    )

    # One-hot encoding
    y_train_cat = keras.utils.to_categorical(y_train, num_classes=num_classes)
    y_val_cat = keras.utils.to_categorical(y_val, num_classes=num_classes)
    y_test_cat = keras.utils.to_categorical(y_test, num_classes=num_classes)

    if verbose:
        print(f"\nTrain set: {x_train.shape[0]} images")
        print(f"  Distribution: {np.bincount(y_train)}")
        print(f"\nValidation set: {x_val.shape[0]} images")
        print(f"  Distribution: {np.bincount(y_val)}")
        print(f"\nTest set: {x_test.shape[0]} images")
        print(f"  Distribution: {np.bincount(y_test)}")

    return x_train, x_val, x_test, y_train_cat, y_val_cat, y_test_cat


def compute_class_weights(
    y_train: np.ndarray, categories: List[str], verbose: bool = True
) -> Dict[int, float]:
    """
    Compute balanced class weights.

    Args:
        y_train: Training labels (integer)
        categories: List of category names
        verbose: Print weight information

    Returns:
        Dictionary mapping class index to weight
    """
    if verbose:
        print("=" * 70)
        print("CLASS WEIGHTING")
        print("=" * 70)

    class_weights_array = compute_class_weight(
        class_weight="balanced", classes=np.unique(y_train), y=y_train
    )

    class_weights = dict(enumerate(class_weights_array))

    if verbose:
        print("\nPoids de classe:")
        for i, cat in enumerate(categories):
            print(f"  {cat:20s}: {class_weights[i]:.3f}")
        print("\n✅ Class weighting activé pour un apprentissage équilibré")

    return class_weights


# pylint: disable=too-many-arguments,too-many-positional-arguments
def create_data_generators(
    x_train: np.ndarray,
    y_train_cat: np.ndarray,
    x_val: np.ndarray,
    y_val_cat: np.ndarray,
    x_test: Optional[np.ndarray] = None,
    y_test_cat: Optional[np.ndarray] = None,
    batch_size: int = 32,
    augment_train: bool = True,
    verbose: bool = True,
) -> Tuple[Any, Any, Optional[Any]]:
    """
    Create Keras data generators with optional augmentation.

    Args:
        x_train: Training images
        y_train_cat: Training labels (one-hot)
        x_val: Validation images
        y_val_cat: Validation labels (one-hot)
        x_test: Test images (optional)
        y_test_cat: Test labels (one-hot, optional)
        batch_size: Batch size
        augment_train: Apply augmentation to training data
        verbose: Print generator information

    Returns:
        Tuple of (train_generator, val_generator, test_generator)
        test_generator is None if x_test not provided
    """
    if verbose:
        print("=" * 70)
        print("DATA AUGMENTATION")
        print("=" * 70)

    # Training generator with augmentation
    if augment_train:
        train_datagen = ImageDataGenerator(
            rotation_range=10,
            width_shift_range=0.1,
            height_shift_range=0.1,
            horizontal_flip=True,
            zoom_range=0.1,
            fill_mode="nearest",
        )
        if verbose:
            print("\n✅ Data augmentation configurée:")
            print("  • Rotation: ±10°")
            print("  • Shift: ±10%")
            print("  • Zoom: ±10%")
            print("  • Horizontal flip")
    else:
        train_datagen = ImageDataGenerator()
        if verbose:
            print("\n⚠️ Pas d'augmentation sur le training set")

    # Validation and test generators (no augmentation)
    val_datagen = ImageDataGenerator()
    test_datagen = ImageDataGenerator()

    if verbose:
        print("\n📊 Création des générateurs...")

    train_generator = train_datagen.flow(
        x_train, y_train_cat, batch_size=batch_size, shuffle=True
    )

    val_generator = val_datagen.flow(
        x_val, y_val_cat, batch_size=batch_size, shuffle=False
    )

    test_generator = None
    if x_test is not None and y_test_cat is not None:
        test_generator = test_datagen.flow(
            x_test, y_test_cat, batch_size=batch_size, shuffle=False
        )

    if verbose:
        print(f"  Train: {len(train_generator)} batches de {batch_size}")
        print(f"  Val:   {len(val_generator)} batches de {batch_size}")
        if test_generator:
            print(f"  Test:  {len(test_generator)} batches de {batch_size}")

    return train_generator, val_generator, test_generator


# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
def create_transfer_learning_generators(
    x_train: np.ndarray,
    y_train_cat: np.ndarray,
    x_val: np.ndarray,
    y_val_cat: np.ndarray,
    x_test: Optional[np.ndarray] = None,
    y_test_cat: Optional[np.ndarray] = None,
    base_model_name: str = "InceptionV3",
    batch_size: int = 32,
    augment_train: bool = True,
    verbose: bool = True,
) -> Tuple[Any, Any, Optional[Any]]:
    """
    Create data generators with model-specific preprocessing.

    Each pretrained model requires its own preprocessing:
    - VGG16/ResNet50: Subtract ImageNet mean
    - InceptionV3: Normalize to [-1, 1]
    - EfficientNetB0: Normalize to [0, 1]

    Args:
        x_train: Training images
        y_train_cat: Training labels (one-hot)
        x_val: Validation images
        y_val_cat: Validation labels (one-hot)
        x_test: Test images (optional)
        y_test_cat: Test labels (one-hot, optional)
        base_model_name: Name of the pretrained model
        batch_size: Batch size
        augment_train: Apply augmentation to training data
        verbose: Print generator information

    Returns:
        Tuple of (train_generator, val_generator, test_generator)
    """
    if verbose:
        print("=" * 70)
        print(f"DATA GENERATORS - {base_model_name.upper()} PREPROCESSING")
        print("=" * 70)

    # Select preprocessing function
    preprocess_funcs = {
        "VGG16": vgg16_preprocess,
        "ResNet50": resnet_preprocess,
        "EfficientNetB0": effnet_preprocess,
        "InceptionV3": inception_preprocess,
    }

    if base_model_name not in preprocess_funcs:
        raise ValueError(f"Preprocessing inconnu pour: {base_model_name}")

    preprocess_func = preprocess_funcs[base_model_name]

    # Training generator with augmentation
    if augment_train:
        train_datagen = ImageDataGenerator(
            preprocessing_function=preprocess_func,
            rotation_range=10,
            width_shift_range=0.05,
            height_shift_range=0.05,
            horizontal_flip=False,  # Medical images - no horizontal flip
            zoom_range=0.05,
            fill_mode="nearest",
        )
        if verbose:
            print("\n✅ Data augmentation configurée:")
            print("  • Rotation: ±10°")
            print("  • Shift: ±5%")
            print("  • Zoom: ±5%")
            print("  • Horizontal flip: NON (images médicales)")
    else:
        train_datagen = ImageDataGenerator(preprocessing_function=preprocess_func)
        if verbose:
            print("\n⚠️ Pas d'augmentation sur le training set")

    # Validation and test generators (no augmentation)
    val_datagen = ImageDataGenerator(preprocessing_function=preprocess_func)
    test_datagen = ImageDataGenerator(preprocessing_function=preprocess_func)

    if verbose:
        print(f"  • Preprocessing: {base_model_name}")
        print("\n📊 Création des générateurs...")

    train_generator = train_datagen.flow(
        x_train, y_train_cat, batch_size=batch_size, shuffle=True
    )

    val_generator = val_datagen.flow(
        x_val, y_val_cat, batch_size=batch_size, shuffle=False
    )

    test_generator = None
    if x_test is not None and y_test_cat is not None:
        test_generator = test_datagen.flow(
            x_test, y_test_cat, batch_size=batch_size, shuffle=False
        )

    if verbose:
        print(f"  Train: {len(train_generator)} batches de {batch_size}")
        print(f"  Val:   {len(val_generator)} batches de {batch_size}")
        if test_generator:
            print(f"  Test:  {len(test_generator)} batches de {batch_size}")

    return train_generator, val_generator, test_generator
