"""
Model building utilities for Jupyter notebooks.

This module provides functions for:
- Custom CNN architecture
- Transfer Learning models (VGG16, ResNet50, EfficientNetB0, InceptionV3)
- Model compilation
- Callbacks creation
- Fine-tuning utilities

Author: Data Pipeline Team
Date: November 2025
"""

import logging
from pathlib import Path
from typing import List, Tuple

import keras
import tensorflow as tf
from keras import layers, models, regularizers
from keras.applications import (
    VGG16,
    EfficientNetB0,
    InceptionV3,
    ResNet50,
)
from keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from keras.losses import CategoricalCrossentropy
from keras.optimizers import Adam

# Configure logger
logger = logging.getLogger(__name__)


# =============================================================================
# CUSTOM CNN
# =============================================================================


def build_custom_cnn(
    input_shape: Tuple[int, int, int] = (128, 128, 3),
    num_classes: int = 4,
    verbose: bool = True,
) -> keras.Model:
    """
    Build a custom CNN architecture optimized for medical imaging.

    Architecture:
        - 5 convolutional blocks (32→64→128→256→512 filters)
        - Batch normalization after each Conv2D
        - Dropout for regularization
        - L2 regularization on dense layers

    Args:
        input_shape: Input image shape (height, width, channels)
        num_classes: Number of output classes
        verbose: Print model information

    Returns:
        Keras model
    """
    if verbose:
        print("=" * 70)
        print("CUSTOM CNN ARCHITECTURE")
        print("=" * 70)

    model = models.Sequential(name="CustomCNN_COVID19")

    # Bloc 1: 32 filtres
    model.add(
        layers.Conv2D(
            32, (3, 3), activation="relu", padding="same", input_shape=input_shape
        )
    )
    model.add(layers.BatchNormalization())
    model.add(layers.Conv2D(32, (3, 3), activation="relu", padding="same"))
    model.add(layers.BatchNormalization())
    model.add(layers.MaxPooling2D((2, 2)))
    model.add(layers.Dropout(0.25))

    # Bloc 2: 64 filtres
    model.add(layers.Conv2D(64, (3, 3), activation="relu", padding="same"))
    model.add(layers.BatchNormalization())
    model.add(layers.Conv2D(64, (3, 3), activation="relu", padding="same"))
    model.add(layers.BatchNormalization())
    model.add(layers.MaxPooling2D((2, 2)))
    model.add(layers.Dropout(0.25))

    # Bloc 3: 128 filtres
    model.add(layers.Conv2D(128, (3, 3), activation="relu", padding="same"))
    model.add(layers.BatchNormalization())
    model.add(layers.Conv2D(128, (3, 3), activation="relu", padding="same"))
    model.add(layers.BatchNormalization())
    model.add(layers.MaxPooling2D((2, 2)))
    model.add(layers.Dropout(0.3))

    # Bloc 4: 256 filtres
    model.add(layers.Conv2D(256, (3, 3), activation="relu", padding="same"))
    model.add(layers.BatchNormalization())
    model.add(layers.Conv2D(256, (3, 3), activation="relu", padding="same"))
    model.add(layers.BatchNormalization())
    model.add(layers.MaxPooling2D((2, 2)))
    model.add(layers.Dropout(0.3))

    # Bloc 5: 512 filtres
    model.add(layers.Conv2D(512, (3, 3), activation="relu", padding="same"))
    model.add(layers.BatchNormalization())
    model.add(layers.Conv2D(512, (3, 3), activation="relu", padding="same"))
    model.add(layers.BatchNormalization())
    model.add(layers.MaxPooling2D((2, 2)))
    model.add(layers.Dropout(0.4))

    # Flatten et couches denses
    model.add(layers.Flatten())
    model.add(
        layers.Dense(512, activation="relu", kernel_regularizer=regularizers.l2(0.001))
    )
    model.add(layers.BatchNormalization())
    model.add(layers.Dropout(0.5))
    model.add(
        layers.Dense(256, activation="relu", kernel_regularizer=regularizers.l2(0.001))
    )
    model.add(layers.BatchNormalization())
    model.add(layers.Dropout(0.5))

    # Couche de sortie
    model.add(layers.Dense(num_classes, activation="softmax"))

    if verbose:
        print("\n✅ Modèle créé")
        print(f"   Nom: {model.name}")
        print(f"   Input shape: {input_shape}")
        print(f"   Output classes: {num_classes}")

    return model


# =============================================================================
# TRANSFER LEARNING
# =============================================================================


# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
def build_transfer_learning_model(
    base_model_name: str = "InceptionV3",
    input_shape: Tuple[int, int, int] = (224, 224, 3),
    num_classes: int = 4,
    freeze_base: bool = True,
    dropout_rate: float = 0.3,
    dense_units: int = 128,
    l2_reg: float = 0.01,
    verbose: bool = True,
) -> Tuple[keras.Model, keras.Model]:
    """
    Build a transfer learning model with pretrained ImageNet weights.

    Supported models:
        - VGG16
        - ResNet50
        - EfficientNetB0
        - InceptionV3

    Args:
        base_model_name: Name of the pretrained model
        input_shape: Input image shape (should be 224x224x3 for most models)
        num_classes: Number of output classes
        freeze_base: If True, freeze base model weights
        dropout_rate: Dropout rate for regularization
        dense_units: Number of units in dense layer
        l2_reg: L2 regularization factor
        verbose: Print model information

    Returns:
        Tuple of (complete_model, base_model)
    """
    if verbose:
        print("=" * 70)
        print(f"TRANSFER LEARNING - {base_model_name.upper()}")
        print("=" * 70)

    # Select base model
    base_models = {
        "VGG16": VGG16,
        "ResNet50": ResNet50,
        "EfficientNetB0": EfficientNetB0,
        "InceptionV3": InceptionV3,
    }

    if base_model_name not in base_models:
        raise ValueError(
            f"Base model inconnu: {base_model_name}. "
            f"Disponibles: {list(base_models.keys())}"
        )

    # Load pretrained base model
    base_model = base_models[base_model_name](
        weights="imagenet", include_top=False, input_shape=input_shape
    )

    # Freeze base model if requested
    base_model.trainable = not freeze_base

    # Build complete model
    model = models.Sequential(
        [
            base_model,
            layers.GlobalAveragePooling2D(),
            layers.Dropout(dropout_rate),
            layers.Dense(
                dense_units,
                activation="relu",
                kernel_regularizer=regularizers.l2(l2_reg),
            ),
            layers.Dropout(dropout_rate),
            layers.Dense(num_classes, activation="softmax"),
        ],
        name=f"{base_model_name}_COVID19",
    )

    if verbose:
        trainable_params = sum(tf.size(w).numpy() for w in model.trainable_weights)
        total_params = sum(tf.size(w).numpy() for w in model.weights)

        print("\n✅ Modèle créé")
        print(f"   Base model: {base_model_name}")
        print(f"   Input shape: {input_shape}")
        print(f"   Output classes: {num_classes}")
        print(f"   Base frozen: {'✅' if freeze_base else '❌'}")
        print("\n📊 Paramètres:")
        print(f"   Trainable:   {trainable_params:,}")
        print(f"   Total:       {total_params:,}")
        print(f"   Ratio:       {trainable_params / total_params:.1%}")

    return model, base_model


def unfreeze_top_layers(
    base_model: keras.Model,
    model: keras.Model,
    n_layers: int = 4,
    learning_rate: float = 5e-5,
    verbose: bool = True,
) -> keras.Model:
    """
    Unfreeze top N layers of base model for fine-tuning.

    Args:
        base_model: Base model to unfreeze
        model: Complete model to recompile
        n_layers: Number of top layers to unfreeze
        learning_rate: Learning rate for fine-tuning (should be small)
        verbose: Print unfreezing information

    Returns:
        Recompiled model ready for fine-tuning
    """
    if verbose:
        print("=" * 70)
        print(f"FINE-TUNING - UNFREEZE TOP {n_layers} LAYERS")
        print("=" * 70)

    # Unfreeze base model
    base_model.trainable = True

    # Freeze all layers except top N
    for layer in base_model.layers[:-n_layers]:
        layer.trainable = False

    if verbose:
        trainable_count = sum(1 for layer in base_model.layers if layer.trainable)
        frozen_count = sum(1 for layer in base_model.layers if not layer.trainable)

        print("\n📊 Base model layers:")
        print(f"   Trainable: {trainable_count}")
        print(f"   Frozen:    {frozen_count}")

    # Recompile with lower learning rate
    model.compile(
        optimizer=Adam(learning_rate=learning_rate),
        loss=CategoricalCrossentropy(),
        metrics=[
            keras.metrics.CategoricalAccuracy(name="accuracy"),
            keras.metrics.Precision(name="precision"),
            keras.metrics.Recall(name="recall"),
        ],
    )

    if verbose:
        trainable_params = sum(tf.size(w).numpy() for w in model.trainable_weights)
        total_params = sum(tf.size(w).numpy() for w in model.weights)

        print("\n📊 Paramètres après unfreeze:")
        print(f"   Trainable: {trainable_params:,}")
        print(f"   Total:     {total_params:,}")
        print(f"   Ratio:     {trainable_params / total_params:.1%}")
        print(f"\n✅ Modèle recompilé avec LR={learning_rate}")

    return model


# =============================================================================
# MODEL COMPILATION & CALLBACKS
# =============================================================================


def compile_model(
    model: keras.Model, learning_rate: float = 0.001, verbose: bool = True
) -> keras.Model:
    """
    Compile a Keras model with standard metrics.

    Args:
        model: Keras model to compile
        learning_rate: Learning rate for Adam optimizer
        verbose: Print compilation information

    Returns:
        Compiled model
    """
    if verbose:
        print("=" * 70)
        print("COMPILATION DU MODÈLE")
        print("=" * 70)

    optimizer = Adam(learning_rate=learning_rate)

    model.compile(
        optimizer=optimizer,
        loss=CategoricalCrossentropy(),
        metrics=[
            keras.metrics.CategoricalAccuracy(name="accuracy"),
            keras.metrics.AUC(name="auc"),
            keras.metrics.Precision(name="precision"),
            keras.metrics.Recall(name="recall"),
        ],
    )

    if verbose:
        print("\n✅ Modèle compilé")
        print(f"   Optimizer: {optimizer.__class__.__name__}")
        print(f"   Learning rate: {learning_rate}")
        print("   Loss: CategoricalCrossentropy")
        print("   Metrics: accuracy, auc, precision, recall")

    return model


def create_callbacks(
    models_dir: Path,
    monitor: str = "val_accuracy",
    patience_early_stop: int = 15,
    patience_reduce_lr: int = 5,
    verbose: bool = True,
) -> List[keras.callbacks.Callback]:
    """
    Create standard training callbacks.

    Args:
        models_dir: Directory to save models
        monitor: Metric to monitor
        patience_early_stop: Patience for early stopping
        patience_reduce_lr: Patience for learning rate reduction
        verbose: Print callback information

    Returns:
        List of Keras callbacks
    """
    if verbose:
        print("=" * 70)
        print("CALLBACKS")
        print("=" * 70)

    models_dir.mkdir(parents=True, exist_ok=True)

    callbacks = [
        EarlyStopping(
            monitor="val_loss",
            patience=patience_early_stop,
            restore_best_weights=True,
            verbose=1 if verbose else 0,
        ),
        ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=patience_reduce_lr,
            min_lr=1e-7,
            verbose=1 if verbose else 0,
        ),
        ModelCheckpoint(
            filepath=str(models_dir / "best_model.keras"),
            monitor=monitor,
            save_best_only=True,
            verbose=1 if verbose else 0,
        ),
    ]

    if verbose:
        print("\n✅ Callbacks configurés:")
        print(f"   • EarlyStopping (patience={patience_early_stop})")
        print(f"   • ReduceLROnPlateau (factor=0.5, patience={patience_reduce_lr})")
        print(f"   • ModelCheckpoint (monitor={monitor})")

    return callbacks
