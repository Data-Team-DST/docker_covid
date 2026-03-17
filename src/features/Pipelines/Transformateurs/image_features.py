"""Image feature extraction transformers for the data pipeline."""

import logging
from typing import Optional, Tuple

import numpy as np  # type: ignore
from sklearn.base import BaseEstimator, TransformerMixin  # type: ignore
from sklearn.decomposition import PCA  # type: ignore
from sklearn.preprocessing import StandardScaler  # type: ignore

# Configuration du logger
logger = logging.getLogger(__name__)


# =========================================================
# =============== 1. IMAGE HISTOGRAM =======================
# =========================================================
class ImageHistogram(BaseEstimator, TransformerMixin):
    """Extract histogram features from images."""

    def __init__(
        self,
        bins: int = 32,
        hist_range: Optional[Tuple[float, float]] = None,
        density: bool = False,
        per_channel: bool = False,
        verbose: bool = True,
    ):
        self._init_params(bins, hist_range, density, per_channel, verbose)

    def _init_params(self, bins, hist_range, density, per_channel, verbose):
        self.bins = bins
        self.hist_range = hist_range
        self.density = density
        self.per_channel = per_channel
        self.verbose = verbose
        self.range_ = None
        self.n_features_ = None

    def fit(self, X, y=None):
        """Fit the transformer by determining feature dimensions."""
        data_array = np.array(X)

        # Détermine la plage de valeurs
        self.range_ = self.hist_range or (data_array.min(), data_array.max())

        # Détermine le nombre de features
        if self.per_channel and len(data_array.shape) == 4:
            self.n_features_ = self.bins * data_array.shape[-1]
        else:
            self.n_features_ = self.bins

        if self.verbose:
            logger.info(
                "Fitted histogram extractor: %d bins, range=%s, %d features",
                self.bins,
                self.range_,
                self.n_features_,
            )

        return self

    def transform(self, X, y=None):
        """Transform images by computing histograms."""
        if self.range_ is None:
            self.fit(X)

        if self.verbose:
            logger.info("Computing histograms for %d images...", len(X))

        data_array = np.array(X)
        histograms = []

        for img in data_array:
            if self.per_channel and len(img.shape) == 3:
                hist_channels = [
                    np.histogram(
                        img[:, :, c].ravel(),
                        bins=self.bins,
                        range=self.range_,
                        density=self.density,
                    )[0]
                    for c in range(img.shape[-1])
                ]
                histogram = np.concatenate(hist_channels)
            else:
                histogram = np.histogram(
                    img.ravel(), bins=self.bins, range=self.range_, density=self.density
                )[0]
            histograms.append(histogram)

        result = np.array(histograms)

        if self.verbose:
            logger.info("Histogram extraction completed. Shape: %s", result.shape)

        return result


# =========================================================
# =============== 2. IMAGE PCA =============================
# =========================================================
class ImagePCA(BaseEstimator, TransformerMixin):
    """Apply PCA dimensionality reduction to images."""

    def __init__(
        self,
        n_components: int = 50,
        whiten: bool = False,
        svd_solver: str = "auto",
        random_state: Optional[int] = None,
        verbose: bool = True,
    ):
        self._init_params(n_components, whiten, svd_solver, random_state, verbose)

    def _init_params(self, n_components, whiten, svd_solver, random_state, verbose):
        self.n_components = n_components
        self.whiten = whiten
        self.svd_solver = svd_solver
        self.random_state = random_state
        self.verbose = verbose
        self.pca_ = None
        self.n_components_ = None
        self.explained_variance_ratio_ = None

    def fit(self, X, y=None):
        """Fit PCA on flattened images."""
        data_array = np.array(X)
        n_samples = data_array.shape[0]
        data_flat = data_array.reshape(n_samples, -1)

        if self.verbose:
            logger.info(
                "Fitting PCA on %d images with shape %s...",
                n_samples,
                data_array.shape[1:],
            )

        self.pca_ = PCA(
            n_components=self.n_components,
            whiten=self.whiten,
            svd_solver=self.svd_solver,
            random_state=self.random_state,
        )
        self.pca_.fit(data_flat)

        self.n_components_ = self.pca_.n_components_
        self.explained_variance_ratio_ = float(
            self.pca_.explained_variance_ratio_.sum()
        )

        if self.verbose:
            logger.info(
                "PCA fitted: %d components, explained variance: %.2f%%",
                self.n_components_,
                self.explained_variance_ratio_ * 100,
            )

        return self

    def transform(self, X, y=None):
        """Transform images using fitted PCA."""
        if self.pca_ is None:
            raise RuntimeError("PCA must be fitted before transform")

        data_array = np.array(X)
        n_samples = data_array.shape[0]
        data_flat = data_array.reshape(n_samples, -1)

        if self.verbose:
            logger.info("Transforming %d images with PCA...", n_samples)

        data_pca = self.pca_.transform(data_flat)

        if self.verbose:
            logger.info("PCA transformation completed. Shape: %s", data_pca.shape)

        return data_pca

    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        """Reconstruct images from PCA components."""
        if self.pca_ is None:
            raise RuntimeError("PCA must be fitted before inverse_transform")

        return self.pca_.inverse_transform(X)


class ImageStandardScaler(BaseEstimator, TransformerMixin):
    """Apply StandardScaler to images.

    This transformer flattens images, applies standardization (z-score),
    and optionally reshapes back to original image dimensions.
    """

    def __init__(
        self,
        with_mean: bool = True,
        with_std: bool = True,
        reshape_output: bool = True,
        verbose: bool = True,
    ):
        self._init_params(with_mean, with_std, reshape_output, verbose)

    def _init_params(self, with_mean, with_std, reshape_output, verbose):
        """Internal parameter initialization (for pylint compliance)."""
        self.with_mean = with_mean
        self.with_std = with_std
        self.reshape_output = reshape_output
        self.verbose = verbose
        self.scaler_ = None
        self.original_shape_ = None

    def fit(self, X, y=None):
        """Fit StandardScaler on flattened images."""
        data_array = np.array(X)
        self.original_shape_ = data_array.shape[1:]
        n_samples = data_array.shape[0]
        data_flat = data_array.reshape(n_samples, -1)

        if self.verbose:
            logger.info("Fitting StandardScaler on %d flattened images...", n_samples)

        self.scaler_ = StandardScaler(with_mean=self.with_mean, with_std=self.with_std)
        self.scaler_.fit(data_flat)

        if self.verbose:
            logger.info(
                "StandardScaler fitted. Mean: %.4f, Std: %.4f",
                self.scaler_.mean_.mean(),
                self.scaler_.scale_.mean(),
            )

        return self

    def transform(self, X, y=None):
        """Transform images using fitted StandardScaler."""
        if self.scaler_ is None:
            raise RuntimeError("StandardScaler must be fitted before transform")

        data_array = np.array(X)
        n_samples = data_array.shape[0]
        data_flat = data_array.reshape(n_samples, -1)

        if self.verbose:
            logger.info("Standardizing %d images...", n_samples)

        data_scaled = self.scaler_.transform(data_flat)

        # Reshape back to original dimensions if requested
        if self.reshape_output:
            data_scaled = data_scaled.reshape(data_array.shape)

        if self.verbose:
            logger.info(
                "Standardization completed. Shape: %s, Mean: %.4f, Std: %.4f",
                data_scaled.shape,
                data_scaled.mean(),
                data_scaled.std(),
            )

        return data_scaled

    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        """Reverse standardization."""
        if self.scaler_ is None:
            raise RuntimeError("StandardScaler must be fitted before inverse_transform")

        original_shape = X.shape
        n_samples = original_shape[0] if len(original_shape) > 2 else None

        # Flatten if needed
        data_flat = X.reshape(n_samples, -1) if n_samples else X

        data_inverse = self.scaler_.inverse_transform(data_flat)

        # Reshape back if needed
        if len(original_shape) > 2 and self.reshape_output:
            data_inverse = data_inverse.reshape(original_shape)

        return data_inverse
