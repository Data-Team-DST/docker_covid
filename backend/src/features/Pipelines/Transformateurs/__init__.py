"""Transformateurs pour le traitement d'images médicales."""

# Image loaders
# Image augmentation
from .image_augmentation import (
    ImageAugmenter,
    ImageRandomCropper,
)

# Image features
from .image_features import (
    ImageHistogram,
    ImagePCA,
    ImageStandardScaler,
)
from .image_loaders import (
    ImageLoader,
)

# Image preprocessing
from .image_preprocessing import (
    ImageBinarizer,
    ImageFlattener,
    ImageMasker,
    ImageNormalizer,
    ImageResizer,
)

# Utilities
from .utilities import (
    SaveTransformer,
    VisualizeTransformer,
)

__all__ = [
    # Loaders
    "ImageLoader",
    # Preprocessing
    "ImageResizer",
    "ImageNormalizer",
    "ImageMasker",
    "ImageFlattener",
    "ImageBinarizer",
    # Augmentation
    "ImageAugmenter",
    "ImageRandomCropper",
    # Features
    "ImageHistogram",
    "ImagePCA",
    "ImageStandardScaler",
    # Utilities
    "VisualizeTransformer",
    "SaveTransformer",
]
