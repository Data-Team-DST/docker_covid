"""
Training and evaluation utilities for Jupyter notebooks.

This module provides functions for:
- Model training with callbacks
- Model evaluation on test data
- Performance metrics calculation

Author: Data Pipeline Team
Date: November 2025
"""

from datetime import datetime
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.metrics import classification_report

import keras

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
        if hasattr(test_generator, 'classes'):
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




# =============================================================================
# RUN METADATA TRACKING
# =============================================================================


# pylint: disable=too-many-arguments,too-many-positional-arguments
def save_run_metadata(
    model_path: Path,
    config: Dict[str, Any],
    history: Optional[keras.callbacks.History] = None,
    metrics: Optional[Dict[str, float]] = None,
    model_architecture: Optional[str] = None,
    additional_info: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Save run metadata alongside the trained model for traceability.

    Creates a JSON file with training configuration, hyperparameters,
    final metrics, and any additional information for reproducibility.

    Args:
        model_path: Path where the model was saved (e.g., 'models/inceptionv3_best.keras')
        config: Configuration dict with hyperparameters
        history: Training history from model.fit()
        metrics: Final evaluation metrics (accuracy, loss, etc.)
        model_architecture: Name of model architecture (e.g., 'InceptionV3', 'CustomCNN')
        additional_info: Any additional metadata to save

    Returns:
        Path to saved metadata JSON file

    Example:
        >>> save_run_metadata(
        ...     model_path=Path("models/inceptionv3_best.keras"),
        ...     config={"batch_size": 32, "epochs": 50},
        ...     history=history,
        ...     metrics={"test_accuracy": 0.95},
        ...     model_architecture="InceptionV3"
        ... )
    """
    print("=" * 70)
    print("SAUVEGARDE MÉTADONNÉES RUN")
    print("=" * 70)

    # Create metadata dict
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "model_path": str(model_path),
        "model_architecture": model_architecture or "Unknown",
    }

    # Add configuration
    if config:
        # Convert Path objects to strings for JSON serialization
        config_serializable = {}
        for key, value in config.items():
            if isinstance(value, Path):
                config_serializable[key] = str(value)
            elif isinstance(value, (list, tuple)) and value and isinstance(value[0], Path):
                config_serializable[key] = [str(v) for v in value]
            else:
                config_serializable[key] = value

        metadata["config"] = config_serializable

    # Add training history (final values)
    if history is not None:
        metadata["training_history"] = {
            "final_epoch": len(history.history["loss"]),
            "total_epochs_trained": len(history.history["loss"]),
            "final_metrics": {
                key: float(values[-1]) for key, values in history.history.items()
            },
        }

    # Add evaluation metrics
    if metrics:
        metadata["evaluation_metrics"] = {
            key: float(value) if isinstance(value, (int, float, np.number)) else str(value)
            for key, value in metrics.items()
            if not isinstance(value, np.ndarray)  # Skip arrays
        }

    # Add additional info
    if additional_info:
        metadata["additional_info"] = additional_info

    # Save to JSON file next to model
    metadata_path = model_path.parent / f"{model_path.stem}_metadata.json"

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Métadonnées sauvegardées: {metadata_path}")
    print(f"   Model: {model_architecture}")
    print(f"   Timestamp: {metadata['timestamp']}")

    if metrics:
        print("\n📊 Métriques finales:")
        for key, value in metrics.items():
            if not isinstance(value, np.ndarray):
                print(f"   {key}: {value}")

    return metadata_path


def load_run_metadata(model_path: Path) -> Dict[str, Any]:
    """
    Load run metadata from JSON file.

    Args:
        model_path: Path to the model file

    Returns:
        Dictionary with run metadata

    Raises:
        FileNotFoundError: If metadata file doesn't exist

    Example:
        >>> metadata = load_run_metadata(Path("models/inceptionv3_best.keras"))
        >>> print(metadata['config']['batch_size'])
        32
    """
    metadata_path = model_path.parent / f"{model_path.stem}_metadata.json"

    if not metadata_path.exists():
        raise FileNotFoundError(f"Métadonnées introuvables: {metadata_path}")

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    print("=" * 70)
    print("CHARGEMENT MÉTADONNÉES")
    print("=" * 70)
    print(f"\n📂 Chargement: {metadata_path}")
    print(f"   Model: {metadata.get('model_architecture', 'Unknown')}")
    print(f"   Timestamp: {metadata.get('timestamp', 'Unknown')}")

    if "evaluation_metrics" in metadata:
        print("\n📊 Métriques:")
        for key, value in metadata["evaluation_metrics"].items():
            print(f"   {key}: {value}")

    if "config" in metadata:
        print("\n⚙️  Configuration:")
        for key, value in metadata["config"].items():
            print(f"   {key}: {value}")

    return metadata