"""Utility transformers for visualization and saving features."""

import os

import matplotlib.pyplot as plt
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin


class VisualizeTransformer(BaseEstimator, TransformerMixin):
    """Transformer de visualisation pour afficher des échantillons d'images."""

    def __init__(self, n_samples=5, prefix="step", save_dir=None):
        self.n_samples = n_samples
        self.prefix = prefix
        self.save_dir = save_dir
        if self.save_dir:
            os.makedirs(self.save_dir, exist_ok=True)

    def fit(self, X, y=None):  # pylint: disable=unused-argument
        """Fit the transformer (no-op for visualization).

        Args:
            X: Input data (unused)
            y: Target data (unused)

        Returns:
            self: Returns self for method chaining
        """
        return self

    def transform(self, X, y=None):  # pylint: disable=unused-argument
        """Transform data by visualizing sample images.

        Args:
            X: Array of images to visualize
            y: Target data (unused)

        Returns:
            np.ndarray: Input data passed through unchanged
        """
        for i in range(min(self.n_samples, len(X))):
            plt.figure()
            title = f"{self.prefix}_sample_{i}"
            if X[i].ndim == 2:
                plt.imshow(X[i], cmap="gray")
            else:
                plt.imshow(X[i])
            plt.title(title)
            plt.axis("off")
            if self.save_dir:
                path = os.path.join(self.save_dir, f"{self.prefix}_sample_{i}.png")
                plt.savefig(path, bbox_inches="tight")
                print(f"Image sauvegardée : {path}")
            plt.show()
            plt.close()
        return X


class SaveTransformer(BaseEstimator, TransformerMixin):
    """Transformer pour sauvegarder les features extraites."""

    def __init__(self, save_dir="outputs", prefix="features"):
        self.save_dir = save_dir
        self.prefix = prefix
        os.makedirs(self.save_dir, exist_ok=True)

    def fit(self, X, y=None):  # pylint: disable=unused-argument
        """Fit the transformer (no-op for saving).

        Args:
            X: Input data (unused)
            y: Target data (unused)

        Returns:
            self: Returns self for method chaining
        """
        return self

    def transform(self, X, y=None):  # pylint: disable=unused-argument
        """Transform data by saving features to disk.

        Args:
            X: Array of features to save
            y: Target data (unused)

        Returns:
            np.ndarray: Input data passed through unchanged
        """
        path = os.path.join(self.save_dir, f"{self.prefix}.npy")
        np.save(path, X)
        print(f"Features sauvegardées dans {path}")
        return X
