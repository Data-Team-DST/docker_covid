"""Image preprocessing transformers for the data pipeline.

FORMATS DE DONNÉES
==================

Ce module manipule les images sous deux formats principaux:

1. **PIL.Image.Image** (Pillow/PIL)
   - Format natif de la bibliothèque Pillow
   - Accès aux dimensions: image.size → (width, height) ⚠️ ATTENTION: Largeur d'abord!
   - Accès aux pixels: image.getpixel((x, y))
   - Modes courants: 'RGB', 'L' (grayscale), 'RGBA'
   - Utilisé par: ImageLoader (sortie), ImageResizer (entrée optionnelle)

2. **numpy.ndarray** (NumPy arrays)
   - Format standard pour le calcul scientifique et le ML
   - Dimensions: array.shape → (height, width, channels) ⚠️ ATTENTION: Hauteur d'abord!
   - Accès aux pixels: array[y, x] ou array[y, x, channel]
   - dtype courants: uint8 (0-255), float32 (0.0-1.0), float64
   - Utilisé par: tous les transformateurs après ImageLoader

CONVENTIONS IMPORTANTES
========================

**Inversion des dimensions:**
- PIL.size: (WIDTH, HEIGHT) - indexation (x, y)
- NumPy.shape: (HEIGHT, WIDTH, CHANNELS) - indexation [y, x, c]

**Exemple concret:**
```python
# Une image 224x224 en RGB
pil_image.size       → (224, 224)          # (width, height)
numpy_array.shape    → (224, 224, 3)        # (height, width, channels)
```

**Flux de données typique dans le pipeline:**
1. ImageLoader: Charge depuis fichier → PIL.Image (RGB ou L)
2. ImageResizer: PIL.Image ou ndarray → ndarray (hauteur, largeur, canaux)
3. ImageNormalizer: ndarray → ndarray (valeurs normalisées 0.0-1.0)
4. ImageMasker: ndarray + masque → ndarray (zones masquées)
5. ImageFlattener: ndarray 3D → ndarray 2D (n_samples, n_features)

**Compatibilité sklearn:**
Tous les transformateurs héritent de BaseEstimator et TransformerMixin,
respectant l'interface fit(X, y=None) / transform(X) pour intégration
dans sklearn.pipeline.Pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np  # type: ignore
from PIL import Image  # type: ignore
from sklearn.base import BaseEstimator, TransformerMixin  # type: ignore
from tqdm import tqdm  # type: ignore

# Logger
logger = logging.getLogger(__name__)

# =============================================================================
# Configuration du rééchantillonnage (resampling filters)
# =============================================================================
# Le rééchantillonnage détermine comment calculer les nouvelles valeurs de pixels
# lors du redimensionnement d'une image. C'est crucial pour la qualité visuelle.
#
# Pillow 10+ a déplacé les constantes de rééchantillonnage dans un sous-module
# `Image.Resampling`. Les versions antérieures les avaient directement dans `Image`.
# Ce bloc assure la compatibilité entre les versions.

try:
    # Pillow >= 10.0: utilise Image.Resampling.LANCZOS
    resampling = Image.Resampling
except AttributeError:  # pragma: no cover
    # Pillow < 10.0: utilise Image.LANCZOS directement
    resampling = Image

# LANCZOS: Filtre de haute qualité (windowed sinc) recommandé pour réduire la taille
# - Meilleure qualité visuelle (préserve les détails fins)
# - Plus lent que NEAREST ou BILINEAR
# - Idéal pour images médicales où la précision compte
# Note: Les filtres Pillow sont des constantes INT (enum) : NEAREST=0, LANCZOS=1, etc.
RESAMPLE_LANCZOS = getattr(resampling, "LANCZOS", getattr(Image, "LANCZOS", 1))

# NEAREST: Algorithme du plus proche voisin
# - Plus rapide mais qualité moindre (effet de pixellisation)
# - Utilisé pour les masques binaires (évite l'interpolation de valeurs 0/1)
# - Pas adapté aux images photographiques
resample_nearest = getattr(resampling, "NEAREST", getattr(Image, "NEAREST", 0))


class ImageResizer(BaseEstimator, TransformerMixin):
    """Resize images to a target size."""

    def __init__(
        self,
        img_size: tuple[int, int] = (256, 256),
        resample: int = RESAMPLE_LANCZOS,
        preserve_aspect_ratio: bool = False,
        verbose: bool = True,
    ):
        """
        Initialize the ImageResizer.

        Args:
            img_size: Target size (width, height) for resized images.
            resample: Filtre de rééchantillonnage à utiliser lors du redimensionnement.
                - LANCZOS (défaut): Haute qualité, préserve les détails (images médicales)
                - BILINEAR: Compromis vitesse/qualité
                - NEAREST: Rapide mais pixellisé (pour masques uniquement)
                Le rééchantillonnage calcule les nouvelles valeurs de pixels lors du resize.
            preserve_aspect_ratio: Si True, conserve les proportions originales
                et ajoute du padding noir. Si False, déforme l'image pour matcher img_size.
            verbose: Whether to log processing information.
        """
        self.img_size = img_size
        self.resample = resample
        self.preserve_aspect_ratio = preserve_aspect_ratio
        self.verbose = verbose
        self.original_shapes_: list[tuple[int, ...]] = []
        self.n_images_processed_: int = 0

    def fit(self, *_: Any) -> ImageResizer:
        """No-op fit to keep sklearn API compatible.
        
        Args:
            *_: Arguments ignorés (X, y, etc.). Le *_ capture tous les arguments
                positionnels mais ne les utilise pas. Convention sklearn : fit(X, y)
                mais ici on n'a pas besoin de y (pas de supervised learning).
        """
        return self

    def _resize_with_aspect_ratio(self, img: Image.Image) -> Image.Image:
        """Resize an image while preserving its aspect ratio.
        
        Stratégie:
        1. Calcule le ratio de redimensionnement (le plus petit des 2 dimensions)
        2. Redimensionne l'image à la nouvelle taille calculée (avec LANCZOS)
        3. Crée une image noire de la taille cible
        4. Colle l'image redimensionnée au centre (padding noir sur les bords)
        
        Exemple: Image 300×400 → 256×256
        - ratio = min(256/300, 256/400) = 0.64
        - new_size = (192, 256)
        - padding horizontal de 32px de chaque côté
        """
        ratio = min(
            self.img_size[0] / img.size[0],
            self.img_size[1] / img.size[1],
        )
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        # Redimensionnement avec le filtre spécifié (LANCZOS par défaut)
        img_resized = img.resize(new_size, self.resample)

        # Création du canvas noir de la taille cible
        new_img = Image.new(img.mode, self.img_size, color=0) # color=0 pour noir
        # Calcul de la position de centrage
        paste_x = (self.img_size[0] - new_size[0]) // 2
        paste_y = (self.img_size[1] - new_size[1]) // 2
        # Collage de l'image redimensionnée au centre
        new_img.paste(img_resized, (paste_x, paste_y))
        return new_img

    def transform(self, X: list[Image.Image | np.ndarray]) -> np.ndarray:
        """
        Resize a list of images to the target size.

        Args:
            X: List of PIL Images or NumPy arrays.

        Returns:
            NumPy array of resized images.
        """
        if self.verbose:
            logger.info("Resizing %d images to %s", len(X), self.img_size)

        self.original_shapes_ = []
        resized: list[np.ndarray] = []
        iterator = tqdm(X, desc="Resizing images") if self.verbose else X

        for img in iterator:
            if isinstance(img, np.ndarray):
                self.original_shapes_.append(img.shape)
                img_obj = Image.fromarray(img.astype(np.uint8))
            else:
                self.original_shapes_.append(img.size)
                img_obj = img

            img_resized = (
                self._resize_with_aspect_ratio(img_obj)
                if self.preserve_aspect_ratio
                else img_obj.resize(self.img_size, self.resample)
            )
            resized.append(np.array(img_resized))

        self.n_images_processed_ = len(resized)
        if self.verbose:
            logger.info(
                "Resizing completed: %d images processed", self.n_images_processed_
            )
        return np.array(resized)


class ImageNormalizer(BaseEstimator, TransformerMixin):
    """Normalize image pixel values."""

    def __init__(
        self,
        method: str = "minmax",
        feature_range: tuple[float, float] = (0.0, 1.0),
        per_image: bool = False,
        verbose: bool = True,
    ):
        """
        Initialize the ImageNormalizer.

        Args:
            method: Normalization method ('minmax', 'standard', 'custom').
            feature_range: Range for 'minmax' or 'custom' normalization.
            per_image: Normalize each image individually if True.
            verbose: Whether to log processing information.
            
        Raises:
            ValueError: If method is not one of 'minmax', 'standard', 'custom'.
        """
        method_lower = method.lower()
        valid_methods = ["minmax", "standard", "custom"]
        if method_lower not in valid_methods:
            raise ValueError(
                f"Invalid method '{method}'. Must be one of {valid_methods}."
            )
        
        self.method = method_lower
        self.feature_range = feature_range
        self.per_image = per_image
        self.verbose = verbose
        self._globals: dict[str, float | None] = {
            "min": None,
            "max": None,
            "mean": None,
            "std": None,
        }

    def fit(self, X: list[np.ndarray] | np.ndarray, y: Any = None) -> ImageNormalizer:
        """Fit normalizer on data (compute global stats if needed).
        
        Args:
            X: Images sur lesquelles calculer les statistiques globales
            y: Ignored, exists for sklearn compatibility
        """
        if not self.per_image:
            arr = np.array(X, dtype=np.float32)
            if self.method in ("minmax", "custom"):
                self._globals["min"] = float(arr.min())
                self._globals["max"] = float(arr.max())
            elif self.method == "standard":
                self._globals["mean"] = float(arr.mean())
                self._globals["std"] = float(arr.std())

            if self.verbose:
                logger.info("Fitted normalizer with method %s", self.method)
        return self

    def transform(self, X: list[np.ndarray] | np.ndarray, y: Any = None) -> np.ndarray:
        """
        Apply normalization to images.

        Args:
            X: List or array of images.
            y: Ignored, exists for sklearn compatibility

        Returns:
            Normalized images as NumPy array.
        """
        if self.verbose:
            logger.info(
                "Normalizing %d images using '%s' method", len(X), self.method
            )
        arr = np.array(X, dtype=np.float32)

        if self.method == "minmax":
            result = self._normalize_minmax(arr)
        elif self.method == "standard":
            result = self._normalize_standard(arr)
        elif self.method == "custom":
            result = self._normalize_custom(arr)
        else:
            raise ValueError(f"Unknown normalization method: {self.method}")

        if self.verbose:
            logger.info(
                "Normalization completed. Output range: [%.2f, %.2f]",
                float(result.min()),
                float(result.max()),
            )
        return result

    def _normalize_minmax(self, arr: np.ndarray) -> np.ndarray:
        """Apply min-max normalization."""
        if self.per_image:
            return np.array([self._minmax_image(img) for img in arr])
        gmin, gmax = self._globals["min"], self._globals["max"]
        if gmin is None or gmax is None:
            raise RuntimeError("Normalizer not fitted for global min/max")
        
        # Protection contre division par zéro
        if gmax == gmin:
            if self.verbose:
                logger.warning("Min equals max (%.2f). Returning zeros.", gmin)
            return np.zeros_like(arr)
        
        return (arr - gmin) / (gmax - gmin)

    def _normalize_standard(self, arr: np.ndarray) -> np.ndarray:
        """Apply standard score normalization."""
        if self.per_image:
            return np.array([self._standardize_image(img) for img in arr])
        gmean, gstd = self._globals["mean"], self._globals["std"]
        if gmean is None or gstd is None:
            raise RuntimeError("Normalizer not fitted for global mean/std")
        return (arr - gmean) / (gstd + 1e-8)

    def _normalize_custom(self, arr: np.ndarray) -> np.ndarray:
        """Apply custom range normalization."""
        fr_min, fr_max = self.feature_range
        if self.per_image:
            return np.array([self._custom_image(img, fr_min, fr_max) for img in arr])
        gmin, gmax = self._globals["min"], self._globals["max"]
        if gmin is None or gmax is None:
            raise RuntimeError("Normalizer not fitted for global min/max")
        
        # Protection contre division par zéro
        if gmax == gmin:
            if self.verbose:
                logger.warning("Min equals max (%.2f). Returning feature_range min.", gmin)
            return np.full_like(arr, fr_min)
        
        normalized = (arr - gmin) / (gmax - gmin)
        return normalized * (fr_max - fr_min) + fr_min

    @staticmethod
    def _minmax_image(img: np.ndarray) -> np.ndarray:
        """Normalize single image with min-max."""
        img_min, img_max = img.min(), img.max()
        return (img - img_min) / (img_max - img_min) if img_max > img_min else img

    @staticmethod
    def _standardize_image(img: np.ndarray) -> np.ndarray:
        """Standardize single image to zero mean and unit variance."""
        img_mean, img_std = img.mean(), img.std()
        return (img - img_mean) / img_std if img_std > 0 else img - img_mean

    @staticmethod
    def _custom_image(img: np.ndarray, fr_min: float, fr_max: float) -> np.ndarray:
        """Normalize single image to a custom range."""
        img_min, img_max = img.min(), img.max()
        if img_max <= img_min:
            return img
        normalized = (img - img_min) / (img_max - img_min)
        return normalized * (fr_max - fr_min) + fr_min


@dataclass
class MaskerConfig:
    """Configuration dataclass for ImageMasker."""

    mask_threshold: float = 0.5
    resize_masks: bool = True
    invert_mask: bool = False
    verbose: bool = True


class ImageMasker(BaseEstimator, TransformerMixin):
    """Apply binary masks to images."""

    def __init__(self, mask_paths: list[str], config: MaskerConfig = MaskerConfig()):
        """
        Initialize the ImageMasker.

        Args:
            mask_paths: List of file paths to mask images.
            config: MaskerConfig dataclass with optional parameters:
                mask_threshold, resize_masks, invert_mask, verbose
        """
        self.mask_paths = mask_paths
        self.mask_threshold = config.mask_threshold
        self.resize_masks = config.resize_masks
        self.invert_mask = config.invert_mask
        self.verbose = config.verbose
        self.n_images_masked_: int = 0

    def fit(self, *_):
        """No-op fit to keep sklearn API compatible.
        
        Args:
            *_: X, y et autres arguments sklearn capturés mais ignorés
        """
        if not self.mask_paths:
            logger.warning("No mask paths provided")
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        Apply binary masks to a list of images.

        Args:
            X: Array of images to mask.

        Returns:
            Masked images as NumPy array.
        """
        if len(self.mask_paths) != len(X):
            raise ValueError(
                f"Number of masks ({len(self.mask_paths)})"
                f" must match number of images ({len(X)})"
            )
        if self.verbose:
            logger.info("Applying masks to %d images", len(X))

        masked = []
        iterator = zip(X, self.mask_paths)
        if self.verbose:
            iterator = tqdm(list(iterator), desc="Applying masks")

        for img, mask_path in iterator:
            try:
                mask = Image.open(mask_path).convert("L")
                if self.resize_masks:
                    target_size = (img.shape[1], img.shape[0])
                    # NEAREST: Évite l'interpolation sur les masques binaires (0/1)
                    # LANCZOS créerait des valeurs intermédiaires (0.3, 0.7...) non désirées
                    mask = mask.resize(target_size, resample_nearest)

                mask_arr = (np.array(mask) / 255.0) > self.mask_threshold
                if self.invert_mask:
                    mask_arr = ~mask_arr
                if img.ndim == 3:
                    mask_arr = mask_arr[:, :, np.newaxis]
                masked.append(img * mask_arr)
            except (OSError, ValueError) as err:
                logger.error("Failed to apply mask %s: %s", mask_path, err)
                masked.append(img)

        self.n_images_masked_ = len(masked)
        if self.verbose:
            logger.info("Masking completed: %d images processed", self.n_images_masked_)
        return np.array(masked)


class ImageFlattener(BaseEstimator, TransformerMixin):
    """Flatten images for ML models."""

    def __init__(self, order: str = "C", verbose: bool = True):
        """
        Initialize the ImageFlattener.

        Args:
            order: Memory order for flattening ('C' or 'F').
            verbose: Whether to log processing information.
        """
        self.order = order
        self.verbose = verbose
        self.original_shape_: tuple[int, ...] = ()
        self.n_features_: int = 0

    def fit(self, X, y=None):
        """
        Fit flattener by storing original shape.

        Args:
            X: Array of images.
            y: Labels (ignored)

        Returns:
            Self.
        """
        arr = np.array(X)
        self.original_shape_ = arr.shape[1:]
        self.n_features_ = int(np.prod(self.original_shape_))
        if self.verbose:
            logger.info(
                "Fitted flattener: %s -> %d features",
                self.original_shape_,
                self.n_features_,
            )
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        Flatten images into 2D array.

        Args:
            X: Array of images.

        Returns:
            Flattened images.
        """
        if self.verbose:
            logger.info("Flattening %d images...", len(X))
        arr = np.array(X)
        n_samples = arr.shape[0]
        data_flat = arr.reshape((n_samples, -1), order=self.order)
        if self.verbose:
            logger.info("Flattening completed: %s -> %s", arr.shape, data_flat.shape)
        return data_flat

    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        """
        Restore flattened images to original shape.

        Args:
            X: Flattened images.

        Returns:
            Images reshaped to original dimensions.
        """
        if not self.original_shape_:
            raise RuntimeError("Transformer must be fitted before inverse_transform")
        n_samples = X.shape[0]
        target_shape = (n_samples,) + self.original_shape_
        return X.reshape(target_shape, order=self.order)


class ImageBinarizer(BaseEstimator, TransformerMixin):
    """Binarize images using threshold."""

    def __init__(
        self,
        threshold: float | str = 0.5,
        invert: bool = False,
        output_dtype=np.float32,
        verbose: bool = True,
    ):
        """
        Initialize the ImageBinarizer.

        Args:
            threshold: Threshold value or method ('mean', 'median', 'otsu').
            invert: Invert the binarization.
            output_dtype: Output data type of binarized images.
            verbose: Whether to log processing information.
        """
        self.threshold = threshold
        self.invert = invert
        self.output_dtype = output_dtype
        self.verbose = verbose
        self.threshold_value_: float | None = None

    def fit(self, X, y=None):
        """
        Fit the binarizer (compute threshold if needed).

        Args:
            X: Array of images.
            y: Labels (ignored)

        Returns:
            Self.
        """
        arr = np.array(X)
        if isinstance(self.threshold, str):
            self.threshold_value_ = self._compute_threshold(arr)
        else:
            self.threshold_value_ = float(self.threshold)
        if self.verbose:
            logger.info("Fitted binarizer with threshold: %.4f", self.threshold_value_)
        return self

    def _compute_threshold(self, arr: np.ndarray) -> float:
        """Compute adaptive threshold based on method."""
        method = str(self.threshold).lower()
        if method == "mean":
            return float(arr.mean())
        if method == "median":
            return float(np.median(arr))
        if method == "otsu":
            return self._compute_otsu_threshold(arr)
        raise ValueError(f"Unknown threshold method: {self.threshold}")

    @staticmethod
    def _compute_otsu_threshold(arr: np.ndarray) -> float:
        """Compute Otsu's threshold for an image."""
        hist, bins = np.histogram(arr.flatten(), bins=256)
        bin_centers = (bins[:-1] + bins[1:]) / 2.0
        max_var = 0.0
        threshold = float(bin_centers[0])
        for t_idx in range(1, len(hist) - 1):
            w0 = hist[:t_idx].sum()
            w1 = hist[t_idx:].sum()
            if w0 == 0 or w1 == 0:
                continue
            mu0 = (hist[:t_idx] * bin_centers[:t_idx]).sum() / w0
            mu1 = (hist[t_idx:] * bin_centers[t_idx:]).sum() / w1
            var = w0 * w1 * (mu0 - mu1) ** 2
            if var > max_var:
                max_var = var
                threshold = float(bin_centers[t_idx])
        return threshold

    def transform(self, X, y=None):
        """
        Apply binarization to images.

        Args:
            X: Array of images.
            y: Labels (ignored)

        Returns:
            Binarized images as NumPy array.
        """
        if self.threshold_value_ is None:
            if isinstance(self.threshold, str):
                raise RuntimeError(
                    "Transformer must be fitted for adaptive thresholding"
                )
            self.threshold_value_ = float(self.threshold)

        if self.verbose:
            logger.info(
                "Binarizing %d images with threshold %.4f",
                len(X),
                self.threshold_value_,
            )

        arr = np.array(X)
        binarized = (
            (arr <= self.threshold_value_).astype(self.output_dtype)
            if self.invert
            else (arr > self.threshold_value_).astype(self.output_dtype)
        )

        if self.verbose:
            positive_ratio = float((binarized == 1).mean() * 100)
            logger.info(
                "Binarization completed. Positive pixels: %.1f%%", positive_ratio
            )

        return binarized
