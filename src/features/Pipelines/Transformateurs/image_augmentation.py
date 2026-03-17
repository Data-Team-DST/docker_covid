"""Image augmentation transformers for the data pipeline."""

import logging
import random
from typing import Optional, Tuple, Union

import numpy as np  # type: ignore
from scipy import ndimage  # type: ignore
from skimage.transform import resize  # type: ignore
from sklearn.base import BaseEstimator, TransformerMixin  # type: ignore
from tqdm import tqdm  # type: ignore

# Configuration du logger
logger = logging.getLogger(__name__)


class ImageAugmenter(BaseEstimator, TransformerMixin):
    """Apply data augmentation to images.

    This transformer applies various augmentation techniques including flips,
    rotations, brightness/contrast adjustments, and noise addition.

    Parameters
    ----------
    flip_horizontal : bool, default=True
        Whether to apply horizontal flip
    flip_vertical : bool, default=False
        Whether to apply vertical flip
    rotation_range : float, default=0
        Maximum rotation angle in degrees (0 to disable)
    brightness_range : tuple or None, default=None
        Range for brightness adjustment as (min, max) multipliers
    noise_std : float, default=0.0
        Standard deviation of Gaussian noise to add (0 to disable)
    zoom_range : tuple or None, default=None
        Range for zoom as (min, max) multipliers
    probability : float, default=0.5
        Probability of applying augmentation to each image
    seed : int or None, default=None
        Random seed for reproducibility
    verbose : bool, default=True
        Whether to display progress messages

    Attributes
    ----------
    n_images_augmented_ : int
        Number of images that received augmentation
    rng_ : np.random.Generator
        Random number generator
    """

    def __init__(
        self,
        flip_horizontal: bool = True,
        flip_vertical: bool = False,
        rotation_range: float = 0,
        brightness_range: Optional[Tuple[float, float]] = None,
        noise_std: float = 0.0,
        zoom_range: Optional[Tuple[float, float]] = None,
        probability: float = 0.5,
        seed: Optional[int] = None,
        verbose: bool = True,
    ):
        self.flip_horizontal = flip_horizontal
        self.flip_vertical = flip_vertical
        self.rotation_range = rotation_range
        self.brightness_range = brightness_range
        self.noise_std = noise_std
        self.zoom_range = zoom_range
        self.probability = probability
        self.seed = seed
        self.verbose = verbose

    def fit(self, X, y=None):
        """Fit the transformer by initializing random state.

        Parameters
        ----------
        X : array-like
            Input data (unused)
        y : array-like, optional
            Target data (unused)

        Returns
        -------
        self : ImageAugmenter
            Returns self for method chaining
        """
        # Generateur de nombres aléatoires
        self.rng_ = np.random.default_rng(self.seed)
        return self

    # self.rng_.random()            Nombre aléatoire 0-1
    # self.rng_.uniform(min, max)  # Nombre dans intervalle
    # self.rng_.normal(mean, std)  # Distribution normale

    def _apply_flip(self, img: np.ndarray) -> np.ndarray:
        """Apply random flips to image."""
        if self.flip_horizontal and self.rng_.random() > 0.5:  # 50% chance
            img = np.fliplr(img)
        if self.flip_vertical and self.rng_.random() > 0.5:
            img = np.flipud(img)
        return img

    def _apply_rotation(self, img: np.ndarray) -> np.ndarray:
        """Apply random rotation to image."""
        if self.rotation_range > 0:
            angle = self.rng_.uniform(-self.rotation_range, self.rotation_range)
            img = ndimage.rotate(img, angle, reshape=False, mode="nearest")
        return img

    def _apply_brightness(self, img: np.ndarray) -> np.ndarray:
        """Apply random brightness adjustment."""
        if self.brightness_range is not None:
            factor = self.rng_.uniform(*self.brightness_range)
            img = np.clip(img * factor, 0, 255 if img.dtype == np.uint8 else 1.0)
        return img

    def _apply_noise(self, img: np.ndarray) -> np.ndarray:
        """Add Gaussian noise to image."""
        if self.noise_std > 0:
            noise = self.rng_.normal(0, self.noise_std, img.shape)
            img = img + noise
            if img.dtype == np.uint8:
                img = np.clip(img, 0, 255).astype(np.uint8)
            else:
                img = np.clip(img, 0, 1)
        return img

    def _apply_zoom(self, img):
        """
        Applique un zoom aléatoire à une image
        tout en conservant la taille originale.
        """
        h, w, c = img.shape

        # Choix aléatoire du facteur de zoom
        zoom_factor = np.random.uniform(self.zoom_range[0], self.zoom_range[1])

        # Calcul de la nouvelle taille
        new_h, new_w = int(h * zoom_factor), int(w * zoom_factor)

        # Redimensionne l'image
        img_zoomed = resize(img, (new_h, new_w, c), anti_aliasing=True)

        # Calcul du padding nécessaire pour revenir à la taille originale
        pad_h = max(h - new_h, 0)
        pad_w = max(w - new_w, 0)

        # Pad (hauteur, largeur, canaux)
        npad = (
            (pad_h // 2, pad_h - pad_h // 2),
            (pad_w // 2, pad_w - pad_w // 2),
            (0, 0),
        )  # pas de padding sur les canaux

        img_padded = np.pad(
            img_zoomed, pad_width=npad, mode="constant", constant_values=0
        )

        # Si le zoom est supérieur à 1, on crop au centre
        if zoom_factor > 1:
            start_h = (new_h - h) // 2
            start_w = (new_w - w) // 2
            img_padded = img_zoomed[start_h : start_h + h, start_w : start_w + w, :]

        return img_padded

    def transform(self, X: np.ndarray, y=None) -> np.ndarray:
        """Transform images by applying augmentation.

        Parameters
        ----------
        X : np.ndarray
            Images to augment
        y : array-like, optional
            Target data (unused)

        Returns
        -------
        np.ndarray
            Augmented images with same shape as input
        """
        if not hasattr(self, "rng_"):
            self.fit(X)

        if self.verbose:
            logger.info(f"Augmenting {len(X)} images (p={self.probability})...")

        data_array = np.array(X)
        original_shape = data_array.shape
        data_aug = []
        n_augmented = 0

        iterator = tqdm(data_array, desc="Augmentation") if self.verbose else data_array

        for img in iterator:
            img_aug = img.copy()
            target_shape = img.shape  # Save original shape of this image

            # Apply augmentation with given probability
            if self.rng_.random() < self.probability:
                img_aug = self._apply_flip(img_aug)
                img_aug = self._apply_rotation(img_aug)
                img_aug = self._apply_brightness(img_aug)
                img_aug = self._apply_noise(img_aug)
                img_aug = self._apply_zoom(img_aug)
                n_augmented += 1

                # Ensure shape consistency after all transforms
                if img_aug.shape != target_shape:
                    # Resize back to original shape if needed
                    from scipy.ndimage import zoom  # type: ignore

                    zoom_factors = [t / s for t, s in zip(target_shape, img_aug.shape)]
                    img_aug = zoom(img_aug, zoom_factors, order=1)

            data_aug.append(img_aug)

        self.n_images_augmented_ = n_augmented

        if self.verbose:
            logger.info(
                f"Augmentation completed: {n_augmented}/{len(X)} "
                f"images augmented ({n_augmented/len(X)*100:.1f}%)"
            )

        result = np.array(data_aug)

        # Final safety check
        if result.shape != original_shape:
            logger.warning("Shape mismatch detected. Forcing shape consistency.")
            result = result.reshape(original_shape)

        return result


class ImageRandomCropper(BaseEstimator, TransformerMixin):
    """Apply random cropping to images.

    This transformer crops random regions from images, useful for data
    augmentation and creating diverse training samples.

    Parameters
    ----------
    crop_size : tuple of int, default=(224, 224)
        Target crop size as (height, width)
    mode : str, default='random'
        Cropping mode: 'random', 'center', or 'corners'
    padding : int or tuple, default=0
        Padding to add before cropping. If int, same padding on all sides.
        If tuple, (pad_height, pad_width)
    pad_mode : str, default='constant'
        Padding mode: 'constant', 'edge', 'reflect', 'wrap'
    seed : int or None, default=None
        Random seed for reproducibility
    verbose : bool, default=True
        Whether to display progress bar

    Attributes
    ----------
    n_images_cropped_ : int
        Number of images successfully cropped
    rng_ : random.Random
        Random number generator
    """

    def __init__(
        self,
        crop_size: Tuple[int, int] = (224, 224),
        mode: str = "random",
        padding: Union[int, Tuple[int, int]] = 0,
        pad_mode: str = "constant",
        seed: Optional[int] = None,
        verbose: bool = True,
    ):
        self.crop_size = crop_size
        self.mode = mode
        self.padding = padding
        self.pad_mode = pad_mode
        self.seed = seed
        self.verbose = verbose

    def fit(self, X, y=None):
        """Fit the transformer by initializing random state.

        Parameters
        ----------
        X : array-like
            Input data (unused)
        y : array-like, optional
            Target data (unused)

        Returns
        -------
        self : ImageRandomCropper
            Returns self for method chaining
        """
        self.rng_ = random.Random(self.seed)
        return self

    def _get_crop_coordinates(
        self, img_height: int, img_width: int, crop_index: int = 0
    ) -> Tuple[int, int]:
        """Get crop coordinates based on mode.

        Parameters
        ----------
        img_height : int
            Image height
        img_width : int
            Image width
        crop_index : int, default=0
            Index for corner mode
            (0-4: top-left, top-right, center, bottom-left, bottom-right)

        Returns
        -------
        tuple
            (top, left) coordinates for crop
        """
        crop_height, crop_width = self.crop_size

        if self.mode == "center":
            top = (img_height - crop_height) // 2
            left = (img_width - crop_width) // 2

        elif self.mode == "corners":
            # Five crop mode: 4 corners + center
            if crop_index == 0:  # top-left
                top, left = 0, 0
            elif crop_index == 1:  # top-right
                top, left = 0, img_width - crop_width
            elif crop_index == 2:  # center
                top = (img_height - crop_height) // 2
                left = (img_width - crop_width) // 2
            elif crop_index == 3:  # bottom-left
                top, left = img_height - crop_height, 0
            else:  # bottom-right
                top, left = img_height - crop_height, img_width - crop_width

        else:  # random
            top = self.rng_.randint(0, max(0, img_height - crop_height))
            left = self.rng_.randint(0, max(0, img_width - crop_width))

        return top, left

    def transform(self, X: np.ndarray, y=None) -> np.ndarray:
        """Transform images by applying random cropping.

        Parameters
        ----------
        X : np.ndarray
            Images to crop
        y : array-like, optional
            Target data (unused)

        Returns
        -------
        np.ndarray
            Cropped images
        """
        if not hasattr(self, "rng_"):
            self.fit(X)

        if self.verbose:
            logger.info(
                f"Cropping {len(X)} images to {self.crop_size}"
                f" (mode: {self.mode})..."
            )

        cropped = []
        n_cropped = 0
        crop_height, crop_width = self.crop_size

        # Handle padding
        if isinstance(self.padding, int):
            pad_h = pad_w = self.padding
        else:
            pad_h, pad_w = self.padding

        iterator = (
            tqdm(X, desc=f"Cropping ({self.mode})") if self.verbose else X
        )

        for img in iterator:
            # Add padding if specified
            if pad_h > 0 or pad_w > 0:
                if len(img.shape) == 2:
                    img = np.pad(
                        img, ((pad_h, pad_h), (pad_w, pad_w)), mode=self.pad_mode
                    )
                else:
                    img = np.pad(
                        img,
                        ((pad_h, pad_h), (pad_w, pad_w), (0, 0)),
                        mode=self.pad_mode,
                    )

            height, width = img.shape[:2]

            # Skip if image is smaller than crop size
            if height < crop_height or width < crop_width:
                logger.warning(
                    f"Image {height}x{width} smaller than crop size"
                    f" {self.crop_size}, skipping"
                )
                cropped.append(img)
                continue

            # Get crop coordinates
            top, left = self._get_crop_coordinates(height, width)

            # Perform crop
            if len(img.shape) == 2:
                img_cropped = img[top : top + crop_height, left : left + crop_width]
            else:
                img_cropped = img[top : top + crop_height, left : left + crop_width, :]

            cropped.append(img_cropped)
            n_cropped += 1

        self.n_images_cropped_ = n_cropped

        if self.verbose:
            logger.info(f"Cropping completed: {n_cropped}/{len(X)} images cropped")
            if cropped:
                logger.info(f"Output shape: {cropped[0].shape}")

        return np.array(cropped)
