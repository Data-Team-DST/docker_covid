"""
Interpretability utilities for Jupyter notebooks.

This module provides functions for:
- Grad-CAM visualization
- LIME explanations
- SHAP values
- Sample selection for analysis

Author: Data Pipeline Team
Date: November 2025
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple

import keras
import matplotlib.pyplot as plt
import numpy as np
from keras.applications.efficientnet import preprocess_input as efficientnet_preprocess

# Import preprocessing functions
from keras.applications.inception_v3 import preprocess_input as inception_preprocess
from keras.applications.resnet50 import preprocess_input as resnet_preprocess
from keras.applications.vgg16 import preprocess_input as vgg16_preprocess

# Import from interpretability module
from src.interpretability.gradcam import GradCAM, visualize_gradcam

# Configure logger
logger = logging.getLogger(__name__)


# =============================================================================
# SETUP
# =============================================================================


def get_preprocessing_function(model_name: str) -> callable:
    """
    Get the appropriate preprocessing function for a transfer learning model.

    Args:
        model_name: Name of the base model ('InceptionV3', 'VGG16', 'ResNet50', 'EfficientNetB0')

    Returns:
        Preprocessing function
    """
    preprocessing_map = {
        "InceptionV3": inception_preprocess,
        "VGG16": vgg16_preprocess,
        "ResNet50": resnet_preprocess,
        "EfficientNetB0": efficientnet_preprocess,
    }

    if model_name not in preprocessing_map:
        raise ValueError(
            f"Unknown model: {model_name}. "
            f"Supported: {list(preprocessing_map.keys())}"
        )

    return preprocessing_map[model_name]


def setup_interpretability(model: keras.Model, verbose: bool = True) -> GradCAM:
    """
    Initialize Grad-CAM for model interpretability.

    Automatically finds the last convolutional layer for Grad-CAM visualization.

    Args:
        model: Trained Keras model
        verbose: Print setup information

    Returns:
        GradCAM object ready for visualization
    """
    if verbose:
        print("=" * 70)
        print("SETUP INTERPRÉTABILITÉ - GRAD-CAM")
        print("=" * 70)

    # Find last convolutional layer
    conv_layer_name = None
    for layer in reversed(model.layers):
        if "conv" in layer.name.lower():
            conv_layer_name = layer.name
            break

    if conv_layer_name is None:
        # For transfer learning models, need to go into base model
        for layer in reversed(model.layers):
            if hasattr(layer, "layers"):  # Sequential or Functional model
                for sublayer in reversed(layer.layers):
                    if "conv" in sublayer.name.lower():
                        conv_layer_name = sublayer.name
                        break
                if conv_layer_name:
                    break

    if conv_layer_name is None:
        raise ValueError("Aucune couche convolutionnelle trouvée dans le modèle!")

    if verbose:
        print("\n✅ Grad-CAM configuré")
        print(f"   Couche convolutionnelle: {conv_layer_name}")
        print(f"   Modèle: {model.name}")

    # Initialize Grad-CAM
    gradcam = GradCAM(model, conv_layer_name)

    return gradcam


# =============================================================================
# SAMPLE SELECTION
# =============================================================================


# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-branches
def select_sample_images(
    x_data: np.ndarray,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: List[str],
    n_samples: int = 2,
    strategy: str = "correct",
    random_seed: int = 42,
) -> Tuple[List[int], List[str]]:
    """
    Select sample images for Grad-CAM analysis.

    Strategies:
        - 'correct': Correctly classified images
        - 'incorrect': Misclassified images
        - 'random': Random selection
        - 'one_per_class': One sample per class (correctly classified)

    Args:
        x_data: Image data
        y_true: True labels
        y_pred: Predicted labels
        class_names: List of class names
        n_samples: Number of samples to select per class
        strategy: Selection strategy
        random_seed: Random seed

    Returns:
        Tuple of (indices, descriptions)
    """
    print("=" * 70)
    print(f"SÉLECTION D'ÉCHANTILLONS - {strategy.upper()}")
    print("=" * 70)

    np.random.seed(random_seed)

    indices = []
    descriptions = []

    if strategy == "correct":
        # Select correctly classified samples
        for class_idx, class_name in enumerate(class_names):
            mask = (y_true == class_idx) & (y_pred == class_idx)
            class_indices = np.where(mask)[0]

            if len(class_indices) > 0:
                selected = np.random.choice(
                    class_indices,
                    size=min(n_samples, len(class_indices)),
                    replace=False,
                )
                indices.extend(selected)
                descriptions.extend([f"{class_name} (correct)"] * len(selected))

        print(f"\n✅ {len(indices)} échantillons correctement classifiés sélectionnés")

    elif strategy == "incorrect":
        # Select misclassified samples
        for class_idx, class_name in enumerate(class_names):
            mask = (y_true == class_idx) & (y_pred != class_idx)
            class_indices = np.where(mask)[0]

            if len(class_indices) > 0:
                selected = np.random.choice(
                    class_indices,
                    size=min(n_samples, len(class_indices)),
                    replace=False,
                )
                indices.extend(selected)

                for idx in selected:
                    pred_class = class_names[y_pred[idx]]
                    descriptions.append(f"{class_name} → {pred_class} (incorrect)")

        print(f"\n✅ {len(indices)} échantillons mal classifiés sélectionnés")

    elif strategy == "one_per_class":
        # Select one correct sample per class
        for class_idx, class_name in enumerate(class_names):
            mask = (y_true == class_idx) & (y_pred == class_idx)
            class_indices = np.where(mask)[0]

            if len(class_indices) > 0:
                selected = np.random.choice(class_indices, size=1)
                indices.extend(selected)
                descriptions.append(f"{class_name} (correct)")

        print(f"\n✅ {len(indices)} échantillons sélectionnés (1 par classe)")

    elif strategy == "random":
        # Random selection
        n_total = min(n_samples * len(class_names), len(x_data))
        indices = np.random.choice(len(x_data), size=n_total, replace=False).tolist()

        for idx in indices:
            true_class = class_names[y_true[idx]]
            pred_class = class_names[y_pred[idx]]
            correct = "✓" if y_true[idx] == y_pred[idx] else "✗"
            descriptions.append(f"{true_class} → {pred_class} {correct}")

        print(f"\n✅ {len(indices)} échantillons aléatoires sélectionnés")

    else:
        raise ValueError(f"Stratégie inconnue: {strategy}")

    # Print summary
    print("\n📊 Résumé:")
    print(f"   Total: {len(indices)} échantillons")
    for desc in set(descriptions):
        count = descriptions.count(desc)
        print(f"   • {desc}: {count}")

    return indices, descriptions


# =============================================================================
# GRAD-CAM ANALYSIS
# =============================================================================


# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
def run_gradcam_analysis(
    gradcam: GradCAM,
    x_data: np.ndarray,
    indices: List[int],
    descriptions: List[str],
    class_names: List[str],
    y_pred_probs: Optional[np.ndarray] = None,
    save_dir: Optional[Path] = None,
    preprocess_fn: Optional[callable] = None,
) -> None:
    """
    Run Grad-CAM analysis on selected samples.

    Args:
        gradcam: GradCAM object
        x_data: Image data (raw images, not preprocessed)
        indices: Indices of samples to analyze
        descriptions: Description for each sample
        class_names: List of class names
        y_pred_probs: Predicted probabilities (optional)
        save_dir: Directory to save figures (optional)
        preprocess_fn: Preprocessing function to apply (e.g., InceptionV3 preprocessing)
    """
    print("=" * 70)
    print(f"ANALYSE GRAD-CAM - {len(indices)} ÉCHANTILLONS")
    print("=" * 70)

    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n💾 Sauvegarde dans: {save_dir}")

    if preprocess_fn is not None:
        print("⚠️  Preprocessing appliqué aux images pour Grad-CAM")

    for i, (idx, desc) in enumerate(zip(indices, descriptions)):
        print(f"\n[{i + 1}/{len(indices)}] {desc}")

        # Get image (raw, pour visualisation)
        img_raw = x_data[idx].copy()

        # Apply preprocessing if provided (pour le modèle)
        if preprocess_fn is not None:
            img_preprocessed = preprocess_fn(x_data[idx].copy())
        else:
            img_preprocessed = img_raw

        # Compute Grad-CAM heatmap (avec image preprocessée)
        heatmap = gradcam.compute_heatmap(
            img_preprocessed, class_idx=None
        )  # Use predicted class

        # Get predicted class info if available
        class_name = ""
        confidence = None
        if y_pred_probs is not None:
            pred_idx = np.argmax(y_pred_probs[idx])
            class_name = class_names[pred_idx]
            confidence = y_pred_probs[idx][pred_idx]

        # Visualize (avec image RAW pour affichage correct)
        # Normaliser l'image raw pour affichage (0-1)
        img_display = img_raw.astype("float32")
        if img_display.max() > 1:
            img_display = img_display / 255.0

        fig = visualize_gradcam(
            img_display,
            heatmap,
            class_name=class_name,
            confidence=confidence,
            alpha=0.4,
            colormap="jet",
        )

        # Add description as super title (override the default title)
        fig.suptitle(desc, fontsize=14, fontweight="bold", y=1.02)

        # Save if requested
        if save_dir:
            save_path = save_dir / f"gradcam_{i + 1:02d}.png"
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            print(f"   💾 Sauvegardé: {save_path.name}")

        plt.show()

    print("\n✅ Analyse Grad-CAM terminée!")
