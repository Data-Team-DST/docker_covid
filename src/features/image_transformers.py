"""
Image Transformation Classes for COVID-19 Image Processing Pipeline

This module contains transformer classes that inherit from BaseTransform
for preprocessing medical images. All transformers are compatible with
sklearn.pipeline.Pipeline.

Transformers included:
    - ImageResizer: Resize images to target dimensions
    - ImageAugmenter: Apply random augmentations (flips, rotation, noise, etc.)
    - ImageNormalizer: Normalize pixel values to [0, 1]
    - ImageMasker: Apply binary masks to images
    - ImageFlattener: Flatten images to 1D vectors
    - ImageRandomCropper: Random crop images
    - RGB_to_L: Convert RGB images to grayscale
    - ImageStandardScaler: Standardize images pixel-wise

Author: DS_COVID Team
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
import numpy as np
import pandas as pd
from tqdm import tqdm
from PIL import Image
from scipy import ndimage
import cv2
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt


# ==============================================================================
# UIHandler - User Interface Manager (Streamlit)
# ==============================================================================

class UIHandler:
    """
    Interface manager for displaying messages.
    
    Automatically switches between Streamlit and console based on use_streamlit parameter.
    Allows using the same code in notebooks and Streamlit applications.
    """
    
    def __init__(self, use_streamlit: bool = False):
        """
        Initialize the UI handler.
        
        Args:
            use_streamlit: Enable Streamlit display if True
        """
        self.use_streamlit = use_streamlit
        
        # Conditional Streamlit import
        if use_streamlit:
            try:
                import streamlit as st
                self.st = st
            except ImportError:
                self.use_streamlit = False
                self.st = None
    
    def info(self, message: str) -> None:
        """Display an information message."""
        if self.use_streamlit and self.st:
            self.st.info(message)
        else:
            print(f"[INFO] {message}")
    
    def success(self, message: str) -> None:
        """Display a success message."""
        if self.use_streamlit and self.st:
            self.st.success(message)
        else:
            print(f"[SUCCESS] {message}")
    
    def warning(self, message: str) -> None:
        """Display a warning message."""
        if self.use_streamlit and self.st:
            self.st.warning(message)
        else:
            print(f"[WARNING] {message}")
    
    def error(self, message: str) -> None:
        """Display an error message."""
        if self.use_streamlit and self.st:
            self.st.error(message)
        else:
            print(f"[ERROR] {message}")


# ==============================================================================
# TransformLogger - Log Manager
# ==============================================================================

class TransformLogger:
    """
    Log manager for transformers.
    
    Centralizes event logging during transformations.
    Uses UIHandler for message display.
    """
    
    def __init__(self, name: str, verbose: bool = True, use_streamlit: bool = False):
        """
        Initialize the logger.
        
        Args:
            name: Transformer name (for identification in logs)
            verbose: Enable detailed logs if True
            use_streamlit: Use Streamlit for display if True
        """
        self.name = name
        self.verbose = verbose
        self.ui = UIHandler(use_streamlit)
    
    def info(self, message: str) -> None:
        """Log an information message."""
        if self.verbose:
            full_message = f"[{self.name}] {message}"
            self.ui.info(full_message)
    
    def warning(self, message: str) -> None:
        """Log a warning."""
        if self.verbose:
            full_message = f"[{self.name}] {message}"
            self.ui.warning(full_message)
    
    def error(self, message: str) -> None:
        """Log an error."""
        full_message = f"[{self.name}] {message}"
        self.ui.error(full_message)


# ==============================================================================
# BaseTransform - Base Class for All Transformers
# ==============================================================================

class BaseTransform(BaseEstimator, TransformerMixin):
    """
    Base class for creating sklearn-compatible transformers.
    
    Principle: A transformer implements ONE abstract method _process()
    that contains the business logic. The rest (logs, UI) is handled automatically.
    
    Compatible with:
    - sklearn.pipeline.Pipeline
    - Pickle serialization
    - Streamlit (optional)
    
    Usage:
        class MyTransform(BaseTransform):
            def _process(self, X):
                # Your transformation logic here
                return X_transformed
    """
    
    def __init__(self, verbose: bool = True, use_streamlit: bool = False):
        """
        Initialize the transformer.
        
        Args:
            verbose: Enable detailed logs if True
            use_streamlit: Enable Streamlit interface if True
        """
        self.verbose = verbose
        self.use_streamlit = use_streamlit
        self._logger = None
    
    @property
    def logger(self) -> TransformLogger:
        """Lazy initialization of logger for pickle compatibility."""
        if self._logger is None:
            self._logger = TransformLogger(
                name=self.__class__.__name__,
                verbose=self.verbose,
                use_streamlit=self.use_streamlit
            )
        return self._logger
    
    def fit(self, X: Any, y: Optional[Any] = None) -> 'BaseTransform':
        """
        Learning phase (sklearn pattern).
        
        Calls _fit() to allow optional learning.
        Returns self to allow chaining.
        """
        self._fit(X, y)
        return self
    
    def transform(self, X: Any) -> Any:
        """
        Transformation phase (sklearn pattern).
        
        Calls _process() which contains the business logic.
        """
        return self._process(X)
    
    def _fit(self, X: Any, y: Optional[Any] = None) -> None:
        """
        Optional learning method.
        
        Override if the transformer requires learning.
        By default, does nothing (stateless transformer).
        """
        pass
    
    @abstractmethod
    def _process(self, X: Any) -> Any:
        """
        Abstract method containing transformation logic.
        
        MUST be implemented by child classes.
        This is where you put your transformation code.
        
        Args:
            X: Data to transform
        
        Returns:
            Transformed data
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _process()"
        )
    
    def _log(self, message: str, level: str = "info") -> None:
        """
        Helper to log messages.
        
        Args:
            message: Message to log
            level: Log level ("info", "warning", "error")
        """
        if level == "warning":
            self.logger.warning(message)
        elif level == "error":
            self.logger.error(message)
        else:
            self.logger.info(message)
    
    def visualize(self, X_before: Any, X_after: Any, n_samples: int = 3) -> None:
        """
        Visualize data before/after transformation.
        
        Override in child classes for specific visualizations.
        
        Args:
            X_before: Data before transformation
            X_after: Data after transformation
            n_samples: Number of samples to visualize
        """
        print(f"\n📊 Visualization of {self.__class__.__name__}")
        print(f"Input shape: {np.array(X_before).shape if hasattr(X_before, '__len__') else 'N/A'}")
        print(f"Output shape: {np.array(X_after).shape if hasattr(X_after, '__len__') else 'N/A'}")


# ==============================================================================
# ImageResizer - Resize images to target dimensions
# ==============================================================================

class ImageResizer(BaseTransform):
    """
    Resize PIL images or numpy arrays to desired dimensions.
    
    This transformer takes images (PIL.Image or numpy arrays) and resizes them
    to a specified target size.
    
    Pattern sklearn: Stateless transformation (no learning).
    
    Supported input formats:
        - List of PIL images
        - List of numpy array images
        - DataFrame with 'image_array' column
    
    Output:
        - 4D numpy array (batch, height, width, channels) or 3D (batch, height, width)
        - DataFrame with updated 'image_array' column
    
    Usage:
        resizer = ImageResizer(img_size=(256, 256))
        images_resized = resizer.fit_transform(images_list)
    """
    
    def __init__(self, img_size=(256, 256), **kwargs):
        """
        Initialize the image resizer.
        
        Args:
            img_size: Tuple (width, height) for target size
            **kwargs: BaseTransform parameters (verbose, use_streamlit)
        """
        super().__init__(**kwargs)
        self.img_size = img_size
    
    def _process(self, X: Any) -> Any:
        """
        Resize images to target size.
        
        Args:
            X: List of images, numpy array or DataFrame
        
        Returns:
            Resized images in same format as input
        
        Raises:
            ValueError: If input format is not supported
        """
        # Case 1: DataFrame with 'image_array' column
        if isinstance(X, pd.DataFrame):
            if 'image_array' not in X.columns:
                raise ValueError("DataFrame must contain 'image_array' column")
            
            self._log(f"Resizing {len(X)} images to {self.img_size} (DataFrame)")
            
            X_transformed = X.copy()
            resized_images = []
            
            for idx, row in tqdm(X.iterrows(), total=len(X),
                                desc=f"[{self.__class__.__name__}] Resizing",
                                disable=not self.verbose):
                img = row['image_array']
                if img is not None:
                    resized_images.append(self._resize_image(img))
                else:
                    resized_images.append(None)
            
            X_transformed['image_array'] = resized_images
            
            return X_transformed
        
        # Case 2: List of images
        elif isinstance(X, list):
            self._log(f"Resizing {len(X)} images to {self.img_size} (list)")
            
            resized = []
            for img in tqdm(X, desc=f"[{self.__class__.__name__}] Resizing",
                           disable=not self.verbose):
                resized.append(self._resize_image(img))
            
            return np.array(resized)
        
        # Case 3: Numpy array (batch of images)
        elif isinstance(X, np.ndarray):
            self._log(f"Resizing {X.shape[0]} images to {self.img_size} (numpy array)")
            
            resized = []
            for img in tqdm(X, desc=f"[{self.__class__.__name__}] Resizing",
                           disable=not self.verbose):
                resized.append(self._resize_image(img))
            
            return np.array(resized)
        
        else:
            raise ValueError(
                f"Unsupported format. Expected: DataFrame, list or ndarray, "
                f"received: {type(X)}"
            )
    
    def _resize_image(self, image: Any) -> np.ndarray:
        """
        Resize a single image.
        
        Args:
            image: Image to resize (numpy array or PIL Image)
        
        Returns:
            Resized image (numpy array)
        """
        # Convert to PIL Image if necessary
        if isinstance(image, np.ndarray):
            # Handle normalized images [0, 1]
            if image.max() <= 1.0:
                image = (image * 255).astype(np.uint8)
            pil_image = Image.fromarray(image)
        else:
            pil_image = image
        
        # Resize
        img_resized = pil_image.resize(self.img_size)
        
        return np.array(img_resized)
    
    def visualize(self, X_before: Any, X_after: Any, n_samples: int = 3) -> None:
        """Visualize resizing before/after."""
        # Extract images from DataFrame if necessary
        if isinstance(X_before, pd.DataFrame):
            images_before = [X_before['image_array'].iloc[i] for i in range(min(n_samples, len(X_before)))]
            images_after = [X_after['image_array'].iloc[i] for i in range(min(n_samples, len(X_after)))]
        else:
            images_before = X_before[:n_samples]
            images_after = X_after[:n_samples]
        
        fig, axes = plt.subplots(2, n_samples, figsize=(4*n_samples, 8))
        fig.suptitle(f'ImageResizer: Resizing to {self.img_size}', fontsize=16, fontweight='bold')
        
        for i in range(n_samples):
            # Before
            axes[0, i].imshow(images_before[i], cmap='gray' if len(images_before[i].shape)==2 else None)
            axes[0, i].set_title(f'Before: {images_before[i].shape}')
            axes[0, i].axis('off')
            
            # After
            axes[1, i].imshow(images_after[i], cmap='gray' if len(images_after[i].shape)==2 else None)
            axes[1, i].set_title(f'After: {images_after[i].shape}')
            axes[1, i].axis('off')
        
        plt.tight_layout()
        plt.show()


# ==============================================================================
# ImageAugmenter - Apply random augmentations
# ==============================================================================

class ImageAugmenter(BaseTransform):
    """
    Apply image augmentation (flips, rotation, noise, brightness, zoom).
    
    This transformer applies random transformations to images to
    increase dataset diversity and improve model generalization.
    
    Pattern sklearn: Stateless transformation with seed for reproducibility.
    
    Available transformations:
        - Horizontal/vertical flips
        - Random rotation
        - Brightness adjustment
        - Gaussian noise
        - Random zoom
    
    Usage:
        augmenter = ImageAugmenter(
            flip_horizontal=True,
            rotation_range=15,
            probability=0.5,
            seed=42
        )
        images_aug = augmenter.fit_transform(images)
    """
    
    def __init__(self, 
                 flip_horizontal=True,
                 flip_vertical=False,
                 rotation_range=0,
                 brightness_range=None,
                 noise_std=0.0,
                 zoom_range=None,
                 probability=0.5,
                 seed=None,
                 **kwargs):
        """
        Initialize the image augmenter.
        
        Args:
            flip_horizontal: Enable horizontal flip
            flip_vertical: Enable vertical flip
            rotation_range: Maximum rotation angle (degrees)
            brightness_range: Tuple (min, max) for brightness adjustment
            noise_std: Standard deviation of Gaussian noise
            zoom_range: Tuple (min, max) for zoom factor
            probability: Probability of applying augmentation to each image
            seed: Seed for reproducibility
            **kwargs: BaseTransform parameters (verbose, use_streamlit)
        """
        super().__init__(**kwargs)
        self.flip_horizontal = flip_horizontal
        self.flip_vertical = flip_vertical
        self.rotation_range = rotation_range
        self.brightness_range = brightness_range
        self.noise_std = noise_std
        self.zoom_range = zoom_range
        self.probability = probability
        self.seed = seed
        self.rng_ = None
        self.n_images_augmented_ = 0
    
    def _fit(self, X: Any, y: Optional[Any] = None) -> None:
        """
        Initialize random number generator.
        
        Args:
            X: Data (unused)
            y: Labels (unused)
        """
        self.rng_ = np.random.default_rng(self.seed)
    
    def _process(self, X: Any) -> Any:
        """
        Apply augmentation to images.
        
        Args:
            X: List of images, numpy array or DataFrame
        
        Returns:
            Augmented images in same format
        """
        if self.rng_ is None:
            self._fit(X)
        
        # Case 1: DataFrame
        if isinstance(X, pd.DataFrame):
            if 'image_array' not in X.columns:
                raise ValueError("DataFrame must contain 'image_array' column")
            
            self._log(f"Augmenting {len(X)} images (p={self.probability}) (DataFrame)")
            
            X_transformed = X.copy()
            aug_images = []
            n_augmented = 0
            
            for idx, row in tqdm(X.iterrows(), total=len(X),
                                desc=f"[{self.__class__.__name__}] Augmentation",
                                disable=not self.verbose):
                img = row['image_array']
                if img is not None and self.rng_.random() < self.probability:
                    aug_images.append(self._augment_image(img))
                    n_augmented += 1
                else:
                    aug_images.append(img)
            
            X_transformed['image_array'] = aug_images
            self.n_images_augmented_ = n_augmented
            
            if self.verbose:
                self._log(f"Augmentation complete: {n_augmented}/{len(X)} images augmented")
            
            return X_transformed
        
        # Case 2: List or numpy array
        else:
            data_array = np.array(X)
            self._log(f"Augmenting {len(data_array)} images (p={self.probability})")
            
            data_aug = []
            n_augmented = 0
            
            iterator = tqdm(data_array, desc=f"[{self.__class__.__name__}] Augmentation",
                           disable=not self.verbose)
            
            for img in iterator:
                if self.rng_.random() < self.probability:
                    data_aug.append(self._augment_image(img))
                    n_augmented += 1
                else:
                    data_aug.append(img)
            
            self.n_images_augmented_ = n_augmented
            
            if self.verbose:
                self._log(f"Augmentation complete: {n_augmented}/{len(data_array)} images augmented")
            
            return np.array(data_aug)
    
    def _augment_image(self, img: np.ndarray) -> np.ndarray:
        """
        Apply random transformations to an image.
        
        Args:
            img: Image to augment (numpy array)
        
        Returns:
            Augmented image (numpy array)
        """
        img_aug = img.copy()
        target_shape = img.shape
        
        # Horizontal flip
        if self.flip_horizontal and self.rng_.random() > 0.5:
            img_aug = np.fliplr(img_aug)
        
        # Vertical flip
        if self.flip_vertical and self.rng_.random() > 0.5:
            img_aug = np.flipud(img_aug)
        
        # Rotation
        if self.rotation_range > 0:
            angle = self.rng_.uniform(-self.rotation_range, self.rotation_range)
            img_aug = ndimage.rotate(img_aug, angle, reshape=False, mode='nearest')
        
        # Brightness
        if self.brightness_range is not None:
            factor = self.rng_.uniform(self.brightness_range[0], self.brightness_range[1])
            img_aug = np.clip(img_aug * factor, 0, 255 if img_aug.max() > 1 else 1)
        
        # Noise
        if self.noise_std > 0:
            noise = self.rng_.normal(0, self.noise_std, img_aug.shape)
            img_aug = np.clip(img_aug + noise, 0, 255 if img_aug.max() > 1 else 1)
        
        # Zoom
        if self.zoom_range is not None:
            zoom_factor = self.rng_.uniform(self.zoom_range[0], self.zoom_range[1])
            h, w = img_aug.shape[:2]
            new_h, new_w = int(h * zoom_factor), int(w * zoom_factor)
            
            if zoom_factor != 1.0:
                # Resize
                img_zoomed = cv2.resize(img_aug, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                
                # Padding or crop to return to original size
                if zoom_factor > 1.0:
                    # Crop at center
                    start_h = (new_h - h) // 2
                    start_w = (new_w - w) // 2
                    img_aug = img_zoomed[start_h:start_h+h, start_w:start_w+w]
                else:
                    # Pad
                    pad_h = (h - new_h) // 2
                    pad_w = (w - new_w) // 2
                    if len(img_aug.shape) == 3:
                        npad = ((pad_h, h - new_h - pad_h), (pad_w, w - new_w - pad_w), (0, 0))
                    else:
                        npad = ((pad_h, h - new_h - pad_h), (pad_w, w - new_w - pad_w))
                    img_aug = np.pad(img_zoomed, npad, mode='constant')
        
        # Ensure shape is preserved
        if img_aug.shape != target_shape:
            if len(target_shape) == 3:
                img_aug = cv2.resize(img_aug, (target_shape[1], target_shape[0]), interpolation=cv2.INTER_LINEAR)
            else:
                img_aug = cv2.resize(img_aug, (target_shape[1], target_shape[0]), interpolation=cv2.INTER_LINEAR)
        
        return img_aug.astype(img.dtype)
    
    def visualize(self, X_before: Any, X_after: Any, n_samples: int = 3) -> None:
        """Visualize augmentation effects."""
        # Extract images
        if isinstance(X_before, pd.DataFrame):
            images_before = [X_before['image_array'].iloc[i] for i in range(min(n_samples, len(X_before)))]
            images_after = [X_after['image_array'].iloc[i] for i in range(min(n_samples, len(X_after)))]
        else:
            images_before = X_before[:n_samples]
            images_after = X_after[:n_samples]
        
        fig, axes = plt.subplots(2, n_samples, figsize=(4*n_samples, 8))
        fig.suptitle(f'ImageAugmenter: Random augmentations (p={self.probability})', fontsize=16, fontweight='bold')
        
        for i in range(n_samples):
            # Before
            axes[0, i].imshow(images_before[i], cmap='gray' if len(images_before[i].shape)==2 else None)
            axes[0, i].set_title(f'Original')
            axes[0, i].axis('off')
            
            # After
            axes[1, i].imshow(images_after[i], cmap='gray' if len(images_after[i].shape)==2 else None)
            axes[1, i].set_title(f'Augmented')
            axes[1, i].axis('off')
        
        plt.tight_layout()
        plt.show()
        
        # Statistics
        print(f"\n📊 Augmentation statistics:")
        print(f"   - Probability: {self.probability}")
        print(f"   - Max rotation: ±{self.rotation_range}°")
        print(f"   - Images augmented: {self.n_images_augmented_}/{len(images_before) if images_before else 0}")


# ==============================================================================
# ImageNormalizer - Normalize pixel values to [0, 1]
# ==============================================================================

class ImageNormalizer(BaseTransform):
    """
    Normalize images pixel-wise between 0 and 1.
    
    This transformer converts image pixels (typically in [0, 255])
    to float values normalized between 0 and 1.
    
    Pattern sklearn: Stateless transformation (no learning).
    
    Supported input formats:
        - List of images (numpy arrays)
        - 4D numpy array (batch of images)
        - DataFrame with 'image_array' column
    
    Output:
        - Normalized images with float32 type
        - Same format as input
    
    Usage:
        normalizer = ImageNormalizer()
        images_norm = normalizer.fit_transform(images)
    """
    
    def _process(self, X: Any) -> Any:
        """
        Normalize images between 0 and 1.
        
        Args:
            X: List of images, numpy array or DataFrame
        
        Returns:
            Normalized images (float32, values between 0 and 1)
        """
        # Case 1: DataFrame
        if isinstance(X, pd.DataFrame):
            if 'image_array' not in X.columns:
                raise ValueError("DataFrame must contain 'image_array' column")
            
            self._log(f"Normalizing {len(X)} images (DataFrame)")
            
            X_transformed = X.copy()
            norm_images = []
            
            for idx, row in tqdm(X.iterrows(), total=len(X),
                                desc=f"[{self.__class__.__name__}] Normalization",
                                disable=not self.verbose):
                img = row['image_array']
                if img is not None:
                    norm_images.append(self._normalize_image(img))
                else:
                    norm_images.append(None)
            
            X_transformed['image_array'] = norm_images
            
            return X_transformed
        
        # Case 2: List or numpy array
        else:
            data_array = np.array(X)
            self._log(f"Normalizing {len(data_array)} images")
            
            # Direct normalization for the whole set
            X_norm = data_array.astype(np.float32)
            
            # Check if already normalized
            if X_norm.max() > 1.0:
                X_norm = X_norm / 255.0
            
            self._log("Normalization complete")
            
            return X_norm
    
    def _normalize_image(self, image: np.ndarray) -> np.ndarray:
        """
        Normalize a single image.
        
        Args:
            image: Image to normalize (numpy array)
        
        Returns:
            Normalized image (float32, values between 0 and 1)
        """
        img_norm = image.astype(np.float32)
        
        # Check if already normalized
        if img_norm.max() > 1.0:
            img_norm = img_norm / 255.0
        
        return img_norm
    
    def visualize(self, X_before: Any, X_after: Any, n_samples: int = 3) -> None:
        """Visualize normalization with histograms."""
        # Extract images
        if isinstance(X_before, pd.DataFrame):
            images_before = [X_before['image_array'].iloc[i] for i in range(min(n_samples, len(X_before)))]
            images_after = [X_after['image_array'].iloc[i] for i in range(min(n_samples, len(X_after)))]
        else:
            images_before = X_before[:n_samples]
            images_after = X_after[:n_samples]
        
        fig, axes = plt.subplots(3, n_samples, figsize=(4*n_samples, 12))
        fig.suptitle('ImageNormalizer: 0-1 Normalization', fontsize=16, fontweight='bold')
        
        for i in range(n_samples):
            # Before
            axes[0, i].imshow(images_before[i], cmap='gray' if len(images_before[i].shape)==2 else None)
            axes[0, i].set_title(f'Before: [{images_before[i].min():.3f}, {images_before[i].max():.3f}]')
            axes[0, i].axis('off')
            
            # After
            axes[1, i].imshow(images_after[i], cmap='gray' if len(images_after[i].shape)==2 else None)
            axes[1, i].set_title(f'After: [{images_after[i].min():.3f}, {images_after[i].max():.3f}]')
            axes[1, i].axis('off')
            
            # Histograms
            axes[2, i].hist(images_before[i].ravel(), bins=50, alpha=0.5, label='Before', color='blue')
            axes[2, i].hist(images_after[i].ravel(), bins=50, alpha=0.5, label='After', color='orange')
            axes[2, i].set_xlabel('Intensity')
            axes[2, i].set_ylabel('Frequency')
            axes[2, i].legend()
            axes[2, i].grid(alpha=0.3)
        
        plt.tight_layout()
        plt.show()


# ==============================================================================
# ImageMasker - Apply binary masks to images
# ==============================================================================

class ImageMasker(BaseTransform):
    """
    Apply binary masks to images.
    
    This transformer multiplies images by their associated masks to
    isolate regions of interest (ROI).
    
    Pattern sklearn: Stateful transformation (mask_paths are stored).
    
    Supported input formats:
        - List of images with mask_paths as parameter
        - Numpy array with mask_paths as parameter
        - DataFrame with 'image_array' and 'mask_path' columns
    
    Usage:
        masker = ImageMasker(mask_paths=mask_list)
        images_masked = masker.fit_transform(images)
        
        # Or with DataFrame
        masker = ImageMasker()
        df_masked = masker.fit_transform(df)  # uses df['mask_path']
    """
    
    def __init__(self, mask_paths=None, **kwargs):
        """
        Initialize the image masker.
        
        Args:
            mask_paths: List of paths to masks (optional if DataFrame)
            **kwargs: BaseTransform parameters (verbose, use_streamlit)
        """
        super().__init__(**kwargs)
        self.mask_paths = mask_paths
    
    def _process(self, X: Any) -> Any:
        """
        Apply masks to images.
        
        Args:
            X: List of images, numpy array or DataFrame
        
        Returns:
            Masked images in same format
        
        Raises:
            ValueError: If mask_paths not provided and DataFrame without 'mask_path'
        """
        # Case 1: DataFrame with 'image_array' and 'mask_path' columns
        if isinstance(X, pd.DataFrame):
            if 'image_array' not in X.columns or 'mask_path' not in X.columns:
                raise ValueError("DataFrame must contain 'image_array' and 'mask_path'")
            
            self._log(f"Applying masks to {len(X)} images (DataFrame)")
            
            X_transformed = X.copy()
            masked_images = []
            
            for idx, row in tqdm(X.iterrows(), total=len(X),
                                desc=f"[{self.__class__.__name__}] Masking",
                                disable=not self.verbose):
                img = row['image_array']
                mask_path = row['mask_path']
                
                if img is not None and pd.notna(mask_path):
                    masked_images.append(self._apply_mask(img, mask_path))
                else:
                    masked_images.append(img)
            
            X_transformed['image_array'] = masked_images
            
            return X_transformed
        
        # Case 2: List or numpy array with mask_paths provided
        else:
            if self.mask_paths is None:
                raise ValueError("mask_paths must be provided for lists/arrays")
            
            data_array = np.array(X)
            
            if len(data_array) != len(self.mask_paths):
                raise ValueError(
                    f"Number of images ({len(data_array)}) != number of masks ({len(self.mask_paths)})"
                )
            
            self._log(f"Applying masks to {len(data_array)} images")
            
            masked = []
            iterator = zip(data_array, self.mask_paths)
            
            for img, mask_path in tqdm(iterator, total=len(data_array),
                                      desc=f"[{self.__class__.__name__}] Masking",
                                      disable=not self.verbose):
                masked.append(self._apply_mask(img, mask_path))
            
            return np.array(masked)
    
    def _apply_mask(self, image: np.ndarray, mask_path: str) -> np.ndarray:
        """
        Apply a mask to an image.
        
        Args:
            image: Image to mask (numpy array)
            mask_path: Path to mask
        
        Returns:
            Masked image (numpy array)
        """
        # Load mask
        mask = Image.open(mask_path).convert('L')
        
        # Resize mask to image size
        if len(image.shape) == 3:
            mask = mask.resize((image.shape[1], image.shape[0]))
        else:
            mask = mask.resize((image.shape[1], image.shape[0]))
        
        # Convert to binary array
        mask_arr = np.array(mask) > 0
        
        # Apply mask
        if len(image.shape) == 3:
            # Color image: expand mask
            mask_arr = mask_arr[:, :, np.newaxis]
        
        return image * mask_arr


# ==============================================================================
# ImageFlattener - Flatten images to 1D vectors
# ==============================================================================

class ImageFlattener(BaseTransform):
    """
    Flatten images to 1D vectors.
    
    This transformer converts 2D or 3D images to 1D vectors,
    necessary for use with some traditional ML algorithms.
    
    Pattern sklearn: Stateless transformation (no learning).
    
    Supported input formats:
        - 3D/4D numpy array (grayscale/color images)
        - DataFrame with 'image_array' column
    
    Output:
        - 2D numpy array (n_samples, n_features)
        - DataFrame with updated 'image_array' column
    
    Usage:
        flattener = ImageFlattener()
        X_flat = flattener.fit_transform(images)  # Shape: (n_samples, height*width*channels)
    """
    
    def _process(self, X: Any) -> Any:
        """
        Flatten images to 1D vectors.
        
        Args:
            X: Numpy array or DataFrame
        
        Returns:
            Flattened images (2D array or DataFrame)
        """
        # Case 1: DataFrame
        if isinstance(X, pd.DataFrame):
            if 'image_array' not in X.columns:
                raise ValueError("DataFrame must contain 'image_array' column")
            
            self._log(f"Flattening {len(X)} images (DataFrame)")
            
            X_transformed = X.copy()
            flat_images = []
            
            for idx, row in tqdm(X.iterrows(), total=len(X),
                                desc=f"[{self.__class__.__name__}] Flattening",
                                disable=not self.verbose):
                img = row['image_array']
                if img is not None:
                    flat_images.append(img.flatten())
                else:
                    flat_images.append(None)
            
            X_transformed['image_array'] = flat_images
            
            return X_transformed
        
        # Case 2: Numpy array
        else:
            data_array = np.array(X)
            n_samples = data_array.shape[0]
            
            self._log(f"Flattening {n_samples} images of shape {data_array.shape}")
            
            # Flatten while preserving first dimension (n_samples)
            X_flat = []
            for img in tqdm(data_array, desc=f"[{self.__class__.__name__}] Flattening",
                           disable=not self.verbose):
                X_flat.append(img.flatten())
            
            X_flat = np.array(X_flat)
            
            self._log(f"Flattening complete. Shape: {X_flat.shape}")
            
            return X_flat


# ==============================================================================
# ImageRandomCropper - Random crop images
# ==============================================================================

class ImageRandomCropper(BaseTransform):
    """
    Perform random crop on each image.
    
    This transformer extracts a random rectangular region from each image.
    Useful for data augmentation and model training.
    
    Pattern sklearn: Stateless transformation with seed for reproducibility.
    
    Usage:
        cropper = ImageRandomCropper(crop_size=(224, 224), seed=42)
        images_cropped = cropper.fit_transform(images)
    """
    
    def __init__(self, crop_size=(224, 224), seed=None, **kwargs):
        """
        Initialize the random cropper.
        
        Args:
            crop_size: Tuple (height, width) for crop size
            seed: Seed for reproducibility
            **kwargs: BaseTransform parameters (verbose, use_streamlit)
        """
        super().__init__(**kwargs)
        self.crop_size = crop_size
        self.seed = seed
        self.rng_ = None
    
    def _fit(self, X: Any, y: Optional[Any] = None) -> None:
        """
        Initialize random number generator.
        
        Args:
            X: Data (unused)
            y: Labels (unused)
        """
        import random
        if self.seed is not None:
            random.seed(self.seed)
            np.random.seed(self.seed)
        self.rng_ = random
    
    def _process(self, X: Any) -> Any:
        """
        Apply random crop to images.
        
        Args:
            X: Images to crop
        
        Returns:
            Cropped images
        """
        if self.rng_ is None:
            self._fit(X)
        
        import random
        
        # Case 1: DataFrame
        if isinstance(X, pd.DataFrame):
            if 'image_array' not in X.columns:
                raise ValueError("DataFrame must contain 'image_array' column")
            
            self._log(f"Random crop of {len(X)} images to {self.crop_size}")
            
            X_transformed = X.copy()
            cropped_images = []
            
            for idx, row in tqdm(X.iterrows(), total=len(X),
                                desc=f"[{self.__class__.__name__}] RandomCrop",
                                disable=not self.verbose):
                img = row['image_array']
                if img is not None:
                    cropped_images.append(self._crop_image(img))
                else:
                    cropped_images.append(None)
            
            X_transformed['image_array'] = cropped_images
            
            return X_transformed
        
        # Case 2: List or numpy array
        else:
            data_array = np.array(X)
            self._log(f"Random crop of {len(data_array)} images")
            
            cropped = []
            for img in tqdm(data_array, desc=f"[{self.__class__.__name__}] RandomCrop",
                           disable=not self.verbose):
                cropped.append(self._crop_image(img))
            
            result = np.array(cropped)
            self._log(f"Random crop complete. Shape: {result.shape}")
            
            return result
    
    def _crop_image(self, img: np.ndarray) -> np.ndarray:
        """
        Crop a single image randomly.
        
        Args:
            img: Image to crop (numpy array)
        
        Returns:
            Cropped image (numpy array)
        """
        import random
        
        h, w = img.shape[:2]
        ch, cw = self.crop_size
        
        # If image is smaller than crop, return as is
        if h < ch or w < cw:
            self._log(f"Image too small ({h}x{w}) for crop ({ch}x{cw}), skipped", level="warning")
            return img
        
        # Random crop position
        top = random.randint(0, h - ch)
        left = random.randint(0, w - cw)
        
        # Crop
        return img[top:top+ch, left:left+cw]


# ==============================================================================
# RGB_to_L - Convert RGB images to grayscale
# ==============================================================================

class RGB_to_L(BaseTransform):
    """
    Convert RGB images to grayscale (Luminance).
    
    This transformer takes color images (RGB) and converts them to
    grayscale using standard PIL/Pillow conversion.
    
    Conversion formula: L = 0.299*R + 0.587*G + 0.114*B
    
    Pattern sklearn: Stateless transformation (no learning).
    
    Supported input formats:
        - DataFrame with 'image_array' column (numpy arrays)
        - List of images (numpy arrays or PIL Images)
        - 4D numpy array (batch of images)
    
    Output:
        - DataFrame with updated 'image_array' column
        - List of grayscale images
        - 3D numpy array (batch of grayscale images)
    
    Usage:
        # With DataFrame
        converter = RGB_to_L()
        df_gray = converter.fit_transform(df)
        
        # With list of images
        images_gray = converter.fit_transform(images_list)
    """
    
    def _process(self, X: Any) -> Any:
        """
        Convert RGB images to grayscale.
        
        Args:
            X: DataFrame, list of images, or numpy array
        
        Returns:
            Same format as input, with converted images
        
        Raises:
            ValueError: If input format is not supported
        """
        # Case 1: DataFrame with 'image_array' column
        if isinstance(X, pd.DataFrame):
            if 'image_array' not in X.columns:
                raise ValueError("DataFrame must contain 'image_array' column")
            
            self._log(f"Converting {len(X)} images (DataFrame)")
            
            X_transformed = X.copy()
            gray_images = []
            
            for idx, row in tqdm(X.iterrows(), total=len(X),
                                desc=f"[{self.__class__.__name__}] RGB → L",
                                disable=not self.verbose):
                img = row['image_array']
                if img is not None:
                    gray_images.append(self._convert_image(img))
                else:
                    gray_images.append(None)
            
            X_transformed['image_array'] = gray_images
            
            # Update number of channels
            if 'channels' in X_transformed.columns:
                X_transformed['channels'] = 1
            
            return X_transformed
        
        # Case 2: List of images
        elif isinstance(X, list):
            self._log(f"Converting {len(X)} images (list)")
            
            gray_images = []
            for img in tqdm(X, desc=f"[{self.__class__.__name__}] RGB → L",
                           disable=not self.verbose):
                gray_images.append(self._convert_image(img))
            
            return gray_images
        
        # Case 3: Numpy array (batch of images)
        elif isinstance(X, np.ndarray):
            if X.ndim != 4:
                raise ValueError(
                    f"Array must be 4D (batch, height, width, channels), received: {X.shape}"
                )
            
            self._log(f"Converting {X.shape[0]} images (numpy array)")
            
            gray_images = []
            for img in tqdm(X, desc=f"[{self.__class__.__name__}] RGB → L",
                           disable=not self.verbose):
                gray_images.append(self._convert_image(img))
            
            return np.array(gray_images)
        
        else:
            raise ValueError(
                f"Unsupported format. Expected: DataFrame, list or ndarray, "
                f"received: {type(X)}"
            )
    
    def _convert_image(self, image: Any) -> np.ndarray:
        """
        Convert a single image to grayscale.
        
        Args:
            image: Image to convert (numpy array or PIL Image)
        
        Returns:
            Grayscale image (2D numpy array)
        """
        # If already grayscale (2D)
        if isinstance(image, np.ndarray) and image.ndim == 2:
            return image
        
        # Convert to PIL Image if necessary
        if isinstance(image, np.ndarray):
            # Handle normalized images [0, 1]
            if image.max() <= 1.0:
                image = (image * 255).astype(np.uint8)
            pil_image = Image.fromarray(image)
        else:
            pil_image = image
        
        # Convert to grayscale
        l_image = pil_image.convert('L')
        
        return np.array(l_image)


# ==============================================================================
# ImageStandardScaler - Standardize images pixel-wise
# ==============================================================================

class ImageStandardScaler(BaseTransform):
    """
    Apply StandardScaler pixel-wise on images.
    
    This transformer standardizes images by subtracting the mean
    and dividing by the standard deviation for each pixel.
    
    Pattern sklearn: Stateful transformation (scaler must be fit).
    
    Usage:
        scaler = ImageStandardScaler()
        scaler.fit(X_train)
        X_train_scaled = scaler.transform(X_train)
        X_test_scaled = scaler.transform(X_test)
    """
    
    def __init__(self, **kwargs):
        """
        Initialize the StandardScaler.
        
        Args:
            **kwargs: BaseTransform parameters (verbose, use_streamlit)
        """
        super().__init__(**kwargs)
        self.scaler = StandardScaler()
        self.original_shape_ = None
    
    def _fit(self, X: Any, y: Optional[Any] = None) -> None:
        """
        Learn statistics (mean, std) on data.
        
        Args:
            X: Training images
            y: Labels (unused)
        """
        # Prepare data
        X_flat, original_shape = self._prepare_data(X, return_shape=True)
        self.original_shape_ = original_shape
        
        self._log(f"Learning StandardScaler on {X_flat.shape}")
        
        # Fit scaler
        self.scaler.fit(X_flat)
        
        self._log("StandardScaler fitted")
    
    def _process(self, X: Any) -> Any:
        """
        Apply standardization to images.
        
        Args:
            X: Images to transform
        
        Returns:
            Standardized images (same format as input)
        """
        # Prepare data
        X_flat, original_shape = self._prepare_data(X, return_shape=True)
        
        self._log(f"Standardizing {X_flat.shape}")
        
        # Transform
        X_scaled = self.scaler.transform(X_flat)
        
        # Reshape if numpy array (not DataFrame)
        if not isinstance(X, pd.DataFrame):
            X_scaled = X_scaled.reshape(original_shape)
        
        self._log(f"Standardization complete. Shape: {X_scaled.shape}")
        
        return X_scaled
    
    def _prepare_data(self, X: Any, return_shape: bool = False):
        """
        Prepare data for StandardScaler (flatten images).
        
        Args:
            X: Images (numpy array, list or DataFrame)
            return_shape: If True, also return original shape
        
        Returns:
            2D numpy array (n_samples, n_features) and optionally the shape
        """
        # Case 1: DataFrame
        if isinstance(X, pd.DataFrame):
            if 'image_array' not in X.columns:
                raise ValueError("DataFrame must contain 'image_array' column")
            
            X_flat = []
            for idx, row in X.iterrows():
                img = row['image_array']
                if img is not None:
                    X_flat.append(img.flatten())
                else:
                    raise ValueError(f"Image None at index {idx}")
            
            X_flat = np.array(X_flat)
            
            if return_shape:
                return X_flat, X_flat.shape
            return X_flat
        
        # Case 2: Numpy array or list
        else:
            data_array = np.array(X)
            original_shape = data_array.shape
            n_samples = data_array.shape[0]
            X_flat = data_array.reshape(n_samples, -1)
            
            if return_shape:
                return X_flat, original_shape
            return X_flat
