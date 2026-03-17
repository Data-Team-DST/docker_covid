"""
Training and evaluation utilities for Jupyter notebooks.

This module provides functions for:
- Model training with callbacks
- Model evaluation on test data
- Performance metrics calculation

Author: Data Pipeline Team
Date: November 2025
"""

import logging
from typing import Dict, List, Optional

import keras
import numpy as np
from sklearn.metrics import classification_report

# ImageDataGenerator is deprecated in Keras 3, use tf.keras version
# pylint: disable=import-error,no-name-in-module
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# Configure logger
logger = logging.getLogger(__name__)


# =============================================================================
# TRAINING
# =============================================================================


# pylint: disable=too-many-arguments,too-many-positional-arguments
def train_model(
    model: keras.Model,
    train_generator: ImageDataGenerator,
    val_generator: ImageDataGenerator,
    class_weights: Optional[Dict[int, float]] = None,
    epochs: int = 100,
    callbacks: Optional[List[keras.callbacks.Callback]] = None,
    verbose: bool = True,
) -> keras.callbacks.History:
    """
    Train a Keras model with data generators.

    Args:
        model: Compiled Keras model
        train_generator: Training data generator
        val_generator: Validation data generator
        class_weights: Class weights for imbalanced datasets
        epochs: Number of training epochs
        callbacks: List of Keras callbacks
        verbose: Verbosity level (0=silent, 1=progress bar, 2=one line per epoch)

    Returns:
        Training history
    """
    print("=" * 70)
    print(f"ENTRAÎNEMENT - {epochs} EPOCHS")
    print("=" * 70)

    if class_weights is not None:
        print("\n📊 Class weights:")
        for cls, weight in class_weights.items():
            print(f"   Classe {cls}: {weight:.3f}")

    print("\n🏋️ Début de l'entraînement...")
    print(f"   Epochs: {epochs}")
    print(f"   Train batches: {len(train_generator)}")
    print(f"   Val batches: {len(val_generator)}")

    history = model.fit(
        train_generator,
        validation_data=val_generator,
        epochs=epochs,
        class_weight=class_weights,
        callbacks=callbacks or [],
        verbose=1 if verbose else 0,
    )

    # Display final results
    final_metrics = {k: v[-1] for k, v in history.history.items()}

    print("\n" + "=" * 70)
    print("RÉSULTATS FINAUX")
    print("=" * 70)

    # Training metrics
    print("\n📈 Training:")
    for metric, value in final_metrics.items():
        if not metric.startswith("val_"):
            print(f"   {metric}: {value:.4f}")

    # Validation metrics
    print("\n📊 Validation:")
    for metric, value in final_metrics.items():
        if metric.startswith("val_"):
            print(f"   {metric}: {value:.4f}")

    print("\n✅ Entraînement terminé!")

    return history


# =============================================================================
# EVALUATION
# =============================================================================


# pylint: disable=too-many-locals
def evaluate_model(
    model: keras.Model,
    test_data,
    class_names: Optional[List[str]] = None,
    verbose: bool = True,
) -> Dict[str, float]:
    """
    Evaluate a Keras model on test data.

    Supports two input formats:
        1. Generator: test_data = test_generator
        2. Arrays: test_data = (X_test, y_test_categorical)

    Args:
        model: Trained Keras model
        test_data: Either a Keras ImageDataGenerator or tuple (X_test, y_test)
        class_names: List of class names for display
        verbose: Print evaluation results

    Returns:
        Dictionary of test metrics including y_true, y_pred, y_pred_probs
    """
    if verbose:
        print("=" * 70)
        print("ÉVALUATION SUR TEST SET")
        print("=" * 70)
        print("\n🧪 Évaluation en cours...")

    # Detect input format
    if isinstance(test_data, tuple):
        # Format: (x_test, y_test_categorical)
        x_test, y_test_cat = test_data

        if verbose:
            print("   Mode: Arrays (x_test, y_test)")
            print(f"   Samples: {len(x_test)}")

        # Evaluate
        test_results = model.evaluate(x_test, y_test_cat, verbose=0)

        # Get predictions
        y_pred_probs = model.predict(x_test, verbose=0)
        y_pred = np.argmax(y_pred_probs, axis=1)
        y_true = np.argmax(y_test_cat, axis=1)

    else:
        # Format: Generator
        test_generator = test_data

        if verbose:
            print("   Mode: Generator")
            print(f"   Batches: {len(test_generator)}")

        # Evaluate
        test_results = model.evaluate(test_generator, verbose=0)

        # Get predictions (reset generator to ensure order)
        test_generator.reset()
        y_pred_probs = model.predict(test_generator, verbose=0)
        y_pred = np.argmax(y_pred_probs, axis=1)

        # Extract y_true from generator
        # DirectoryIterator has .classes, NumpyArrayIterator doesn't
        if hasattr(test_generator, "classes"):
            y_true = test_generator.classes
        else:
            # For NumpyArrayIterator, extract labels from batches
            test_generator.reset()
            y_true_cat = []
            for i in range(len(test_generator)):
                _, y_batch = test_generator[i]
                y_true_cat.append(y_batch)
            y_true_cat = np.concatenate(y_true_cat, axis=0)
            y_true = np.argmax(y_true_cat, axis=1)

    # Get metric names
    metric_names = model.metrics_names

    # Create results dictionary
    results = dict(zip(metric_names, test_results))

    if verbose:
        print("\n" + "=" * 70)
        print("RÉSULTATS TEST")
        print("=" * 70)

        for metric, value in results.items():
            print(f"   {metric}: {value:.4f}")

    # Calculate per-class metrics
    if class_names is None:
        class_names = [f"Class {i}" for i in range(len(np.unique(y_true)))]

    if verbose:
        print("\n" + "=" * 70)
        print("CLASSIFICATION REPORT")
        print("=" * 70)
        print(classification_report(y_true, y_pred, target_names=class_names, digits=4))

    # Add predictions to results
    results["y_true"] = y_true
    results["y_pred"] = y_pred
    results["y_pred_probs"] = y_pred_probs

    if verbose:
        print("\n✅ Évaluation terminée!")

    return results
