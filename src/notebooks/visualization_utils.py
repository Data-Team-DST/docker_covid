"""
Visualization utilities for Jupyter notebooks.

This module provides functions for:
- Training history plots
- Confusion matrix visualization
- Performance metrics visualization

Author: Data Pipeline Team
Date: November 2025
"""

import logging
from typing import List, Optional

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import keras
from sklearn.metrics import confusion_matrix

# Configure logger
logger = logging.getLogger(__name__)

# Configure plot style
plt.style.use("seaborn-v0_8-darkgrid")
sns.set_palette("husl")

# =============================================================================
# IMAGE VISUALIZATION
# =============================================================================


# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
def visualize_images(
    images: np.ndarray,
    labels: Optional[List[str]] = None,
    n_samples: int = 12,
    n_cols: int = 4,
    figsize: tuple = (15, 12),
    title: str = "Images Préprocessées",
    save_path: Optional[str] = None,
    random_seed: int = 42,
) -> None:
    """
    Visualize a grid of preprocessed images.

    Args:
        images: Array of images (N, H, W, C) or (N, H, W)
        labels: Optional list of labels for each image
        n_samples: Number of samples to display
        n_cols: Number of columns in the grid
        figsize: Figure size (width, height)
        title: Figure title
        save_path: Path to save figure (optional)
        random_seed: Random seed for sample selection
    """
    print("=" * 70)
    print("VISUALISATION D'IMAGES")
    print("=" * 70)

    np.random.seed(random_seed)
    n_images = len(images)
    n_samples = min(n_samples, n_images)

    # Select random samples
    indices = np.random.choice(n_images, size=n_samples, replace=False)

    # Calculate grid dimensions
    n_rows = (n_samples + n_cols - 1) // n_cols

    # Create figure
    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
    axes = axes.flatten() if n_samples > 1 else [axes]

    print(f"\n📊 Affichage de {n_samples} images")
    print(f"   Shape: {images.shape}")
    print(f"   Range: [{images.min():.3f}, {images.max():.3f}]")

    for i, idx in enumerate(indices):
        img = images[idx]

        # Normalize image for display if needed
        if img.max() > 1:
            img_display = img / 255.0
        else:
            img_display = img.copy()

        # Handle grayscale
        if len(img.shape) == 2 or img.shape[-1] == 1:
            axes[i].imshow(img_display.squeeze(), cmap="gray")
        else:
            axes[i].imshow(img_display)

        # Add label if provided
        if labels is not None:
            axes[i].set_title(f"{labels[idx]}", fontsize=10, fontweight="bold")
        else:
            axes[i].set_title(f"Image {idx}", fontsize=10)

        axes[i].axis("off")

    # Hide unused subplots
    for i in range(n_samples, len(axes)):
        axes[i].axis("off")

    plt.suptitle(title, fontsize=16, fontweight="bold", y=0.98)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"\n💾 Figure sauvegardée: {save_path}")

    plt.show()
    print("\n✅ Images affichées!")


# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
def visualize_masked_images(
    images: np.ndarray,
    masks: np.ndarray,
    labels: Optional[List[str]] = None,
    n_samples: int = 6,
    n_cols: int = 3,
    figsize: tuple = (15, 10),
    save_path: Optional[str] = None,
    random_seed: int = 42,
) -> None:
    """
    Visualize original images alongside their masks and masked versions.

    Args:
        images: Array of original images (N, H, W, C) or (N, H, W)
        masks: Array of binary masks (N, H, W) or (N, H, W, 1)
        labels: Optional list of labels for each image
        n_samples: Number of samples to display
        n_cols: Number of columns (each row shows: original, mask, masked)
        figsize: Figure size (width, height)
        save_path: Path to save figure (optional)
        random_seed: Random seed for sample selection
    """
    print("=" * 70)
    print("VISUALISATION IMAGES MASQUÉES")
    print("=" * 70)

    np.random.seed(random_seed)
    n_images = len(images)
    n_samples = min(n_samples, n_images)

    # Select random samples
    indices = np.random.choice(n_images, size=n_samples, replace=False)

    # Create figure - 3 columns per sample (original, mask, masked)
    n_rows = n_samples
    fig, axes = plt.subplots(n_rows, 3, figsize=figsize)

    # Ensure axes is 2D
    if n_samples == 1:
        axes = axes.reshape(1, -1)

    print(f"\n📊 Affichage de {n_samples} images avec masques")
    print(f"   Images shape: {images.shape}")
    print(f"   Masks shape: {masks.shape}")

    for i, idx in enumerate(indices):
        img = images[idx]
        mask = masks[idx]

        # Normalize for display
        if img.max() > 1:
            img_display = img / 255.0
        else:
            img_display = img.copy()

        # Ensure mask is 2D
        if len(mask.shape) == 3 and mask.shape[-1] == 1:
            mask = mask.squeeze()

        # Create masked version
        if len(img.shape) == 3 and img.shape[-1] == 3:
            masked_img = img_display * mask[..., np.newaxis]
        else:
            masked_img = img_display * mask

        # Plot original
        if len(img.shape) == 2 or img.shape[-1] == 1:
            axes[i, 0].imshow(img_display.squeeze(), cmap="gray")
        else:
            axes[i, 0].imshow(img_display)
        axes[i, 0].set_title("Original", fontsize=10, fontweight="bold")
        axes[i, 0].axis("off")

        # Plot mask
        axes[i, 1].imshow(mask, cmap="gray")
        axes[i, 1].set_title("Mask", fontsize=10, fontweight="bold")
        axes[i, 1].axis("off")

        # Plot masked
        if len(img.shape) == 2 or img.shape[-1] == 1:
            axes[i, 2].imshow(masked_img.squeeze(), cmap="gray")
        else:
            axes[i, 2].imshow(masked_img)
        axes[i, 2].set_title("Masked", fontsize=10, fontweight="bold")
        axes[i, 2].axis("off")

        # Add label as ylabel
        if labels is not None:
            axes[i, 0].set_ylabel(
                f"{labels[idx]}", fontsize=11, fontweight="bold", rotation=0, ha="right"
            )

    plt.suptitle(
        "Comparaison: Original vs Mask vs Masked", fontsize=16, fontweight="bold", y=0.995
    )
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"\n💾 Figure sauvegardée: {save_path}")

    plt.show()
    print("\n✅ Images masquées affichées!")


# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
def compare_preprocessing_steps(
    images_raw: np.ndarray,
    images_preprocessed: np.ndarray,
    labels: Optional[List[str]] = None,
    n_samples: int = 4,
    figsize: tuple = (12, 10),
    save_path: Optional[str] = None,
    random_seed: int = 42,
) -> None:
    """
    Compare images before and after preprocessing side-by-side.

    Args:
        images_raw: Array of raw images (N, H, W, C)
        images_preprocessed: Array of preprocessed images (N, H, W, C)
        labels: Optional list of labels
        n_samples: Number of samples to display
        figsize: Figure size (width, height)
        save_path: Path to save figure (optional)
        random_seed: Random seed for sample selection
    """
    print("=" * 70)
    print("COMPARAISON PREPROCESSING")
    print("=" * 70)

    np.random.seed(random_seed)
    n_images = len(images_raw)
    n_samples = min(n_samples, n_images)

    # Select random samples
    indices = np.random.choice(n_images, size=n_samples, replace=False)

    # Create figure - 2 columns (before, after)
    fig, axes = plt.subplots(n_samples, 2, figsize=figsize)

    # Ensure axes is 2D
    if n_samples == 1:
        axes = axes.reshape(1, -1)

    print(f"\n📊 Comparaison de {n_samples} images")
    print(f"   Raw range: [{images_raw.min():.1f}, {images_raw.max():.1f}]")
    print(f"   Preprocessed range: [{images_preprocessed.min():.3f}, {images_preprocessed.max():.3f}]")

    for i, idx in enumerate(indices):
        img_raw = images_raw[idx]
        img_prep = images_preprocessed[idx]

        # Normalize raw for display
        if img_raw.max() > 1:
            img_raw_display = img_raw / 255.0
        else:
            img_raw_display = img_raw

        # Normalize preprocessed for display
        if img_prep.min() < 0:  # InceptionV3/ResNet style [-1, 1]
            img_prep_display = (img_prep + 1) / 2
        elif img_prep.max() > 1:
            img_prep_display = img_prep / 255.0
        else:
            img_prep_display = img_prep

        # Plot raw
        if len(img_raw.shape) == 2 or img_raw.shape[-1] == 1:
            axes[i, 0].imshow(img_raw_display.squeeze(), cmap="gray")
        else:
            axes[i, 0].imshow(img_raw_display)
        axes[i, 0].set_title("Before", fontsize=10, fontweight="bold")
        axes[i, 0].axis("off")

        # Plot preprocessed
        if len(img_prep.shape) == 2 or img_prep.shape[-1] == 1:
            axes[i, 1].imshow(img_prep_display.squeeze(), cmap="gray")
        else:
            axes[i, 1].imshow(img_prep_display)
        axes[i, 1].set_title("After", fontsize=10, fontweight="bold")
        axes[i, 1].axis("off")

        # Add label
        if labels is not None:
            axes[i, 0].set_ylabel(
                f"{labels[idx]}", fontsize=11, fontweight="bold", rotation=0, ha="right"
            )

    plt.suptitle("Preprocessing: Avant vs Après", fontsize=16, fontweight="bold", y=0.995)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"\n💾 Figure sauvegardée: {save_path}")

    plt.show()
    print("\n✅ Comparaison affichée!")

# =============================================================================
# TRAINING HISTORY
# =============================================================================


# pylint: disable=too-many-locals
def plot_training_curves(
    history: keras.callbacks.History,
    history_ft: Optional[keras.callbacks.History] = None,
    figsize: tuple = (16, 5),
    save_path: Optional[str] = None,
) -> None:
    """
    Plot training and validation curves.

    Supports both single-phase and two-phase training (Feature Extraction + Fine-Tuning).

    Args:
        history: Training history from model.fit()
        history_ft: Optional fine-tuning history (for transfer learning)
        figsize: Figure size (width, height)
        save_path: Path to save figure (optional)
    """
    print("=" * 70)
    print("COURBES D'ENTRAÎNEMENT")
    print("=" * 70)

    # Combine histories if fine-tuning exists
    if history_ft is not None:
        print("\n📊 Mode: Feature Extraction + Fine-Tuning")
        epochs_fe = len(history.history["loss"])

        combined_history = {}
        for key in history.history.keys():
            combined_history[key] = history.history[key] + history_ft.history[key]
    else:
        print("\n📊 Mode: Single-phase training")
        combined_history = history.history
        epochs_fe = None

    # Get available metrics
    available_metrics = [k for k in combined_history.keys() if not k.startswith("val_")]

    # Plot Loss + 3 metrics
    metrics_to_plot = ["loss"] + [m for m in available_metrics if m != "loss"][:3]

    _, axes = plt.subplots(1, len(metrics_to_plot), figsize=figsize)

    if len(metrics_to_plot) == 1:
        axes = [axes]

    for idx, metric in enumerate(metrics_to_plot):
        ax = axes[idx]

        # Plot training
        epochs = range(1, len(combined_history[metric]) + 1)
        ax.plot(
            epochs,
            combined_history[metric],
            label=f"Train {metric}",
            linewidth=2,
            marker="o",
            markersize=3,
        )

        # Plot validation if exists
        val_metric = f"val_{metric}"
        if val_metric in combined_history:
            ax.plot(
                epochs,
                combined_history[val_metric],
                label=f"Val {metric}",
                linewidth=2,
                marker="s",
                markersize=3,
            )

        # Add vertical line for fine-tuning start
        if epochs_fe is not None:
            ax.axvline(
                x=epochs_fe,
                color="red",
                linestyle="--",
                linewidth=2,
                label="Fine-tuning start",
                alpha=0.7,
            )

        ax.set_xlabel("Epoch", fontsize=12)
        ax.set_ylabel(metric.capitalize(), fontsize=12)
        ax.set_title(
            f"{metric.capitalize()} over Epochs", fontsize=14, fontweight="bold"
        )
        ax.legend(loc="best", fontsize=10)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"\n💾 Figure sauvegardée: {save_path}")

    plt.show()

    # Print summary
    print("\n📈 Résumé:")
    final_metrics = {k: v[-1] for k, v in combined_history.items()}

    print("\n   Training:")
    for metric in metrics_to_plot:
        if metric in final_metrics:
            print(f"      {metric}: {final_metrics[metric]:.4f}")

    print("\n   Validation:")
    for metric in metrics_to_plot:
        val_metric = f"val_{metric}"
        if val_metric in final_metrics:
            print(f"      {val_metric}: {final_metrics[val_metric]:.4f}")

    print("\n✅ Courbes affichées!")


# =============================================================================
# CONFUSION MATRIX
# =============================================================================


# pylint: disable=too-many-arguments,too-many-positional-arguments
def plot_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: List[str],
    normalize: bool = True,
    figsize: tuple = (10, 8),
    save_path: Optional[str] = None,
) -> None:
    """
    Plot confusion matrix with annotations.

    Args:
        y_true: True labels
        y_pred: Predicted labels
        class_names: List of class names
        normalize: If True, show percentages instead of counts
        figsize: Figure size (width, height)
        save_path: Path to save figure (optional)
    """
    print("=" * 70)
    print("MATRICE DE CONFUSION")
    print("=" * 70)

    # Compute confusion matrix
    cm = confusion_matrix(y_true, y_pred)

    # Normalize if requested
    if normalize:
        cm_display = cm.astype("float") / cm.sum(axis=1)[:, np.newaxis]
        fmt = ".2%"
        print("\n📊 Mode: Normalisé (pourcentages)")
    else:
        cm_display = cm
        fmt = "d"
        print("\n📊 Mode: Valeurs brutes (counts)")

    # Create figure
    plt.figure(figsize=figsize)

    # Plot heatmap
    sns.heatmap(
        cm_display,
        annot=True,
        fmt=fmt,
        cmap="Blues",
        xticklabels=class_names,
        yticklabels=class_names,
        cbar_kws={"label": "Proportion" if normalize else "Count"},
        linewidths=0.5,
        linecolor="gray",
    )

    plt.title("Matrice de Confusion", fontsize=16, fontweight="bold", pad=20)
    plt.ylabel("Vraie Classe", fontsize=13)
    plt.xlabel("Classe Prédite", fontsize=13)
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"\n💾 Figure sauvegardée: {save_path}")

    plt.show()

    # Print statistics
    print("\n📊 Statistiques:")
    print(f"   Total samples: {cm.sum()}")
    print(f"   Correct predictions: {np.trace(cm)}")
    print(f"   Overall accuracy: {np.trace(cm) / cm.sum():.2%}")

    # Per-class accuracy
    print("\n   Accuracy per class:")
    for i, class_name in enumerate(class_names):
        class_acc = cm[i, i] / cm[i].sum() if cm[i].sum() > 0 else 0
        print(f"      {class_name}: {class_acc:.2%} ({cm[i, i]}/{cm[i].sum()})")

    print("\n✅ Matrice affichée!")
