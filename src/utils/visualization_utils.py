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

import keras
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import confusion_matrix

# Configure logger
logger = logging.getLogger(__name__)

# Configure plot style
plt.style.use("seaborn-v0_8-darkgrid")
sns.set_palette("husl")


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
