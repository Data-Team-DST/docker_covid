"""
Package de transformateurs pour le pipeline de traitement d'images COVID-19.

Ce package contient tous les transformateurs nécessaires pour charger,
préprocesser, analyser et extraire des features d'images médicales.
"""

from .base import BaseTransform, TransformLogger, UIHandler
from .DatasetStatistics import DatasetStatistics
from .ImageAnalyser import ImageAnalyser
from .ImageAugmenter import ImageAugmenter
from .ImagePCA import ImagePCA
from .ImageRandomCropper import ImageRandomCropper
from .loaders import ImagePathLoader, TupleToDataFrame

# Preprocessing transformers (sous-package processing/)
from .processing.ImageFlattener import ImageFlattener
from .processing.ImageMasker import ImageMasker
from .processing.ImageNormalizer import ImageNormalizer
from .processing.ImageResizer import ImageResizer
from .processing.ImageStandardScaler import ImageStandardScaler
from .processing.RGB_to_L import RGB_to_L
from .SaveTransformer import SaveTransformer
from .TrainTestSplitter import TrainTestSplitter

# Visualization transformers (sous-package visualization/)
from .visualization.HistogramVisualizer import HistogramVisualizer
from .visualization.ImageComparisonVisualizer import ImageComparisonVisualizer
from .visualization.ImageHistogram import ImageHistogram
from .visualization.PCAVisualizer import PCAVisualizer
from .visualization.VisualizeTransformer import VisualizeTransformer

__all__ = [
    # Classes de base
    "BaseTransform",
    "UIHandler",
    "TransformLogger",
    # Loaders
    "ImagePathLoader",
    "TupleToDataFrame",
    # Preprocessing
    "ImageResizer",
    "ImageAugmenter",
    "ImageNormalizer",
    "ImageMasker",
    "ImageFlattener",
    "ImageRandomCropper",
    "ImageStandardScaler",
    "RGB_to_L",
    # Analyse et features
    "ImageAnalyser",
    "ImagePCA",
    "ImageHistogram",
    # Utilities
    "SaveTransformer",
    "VisualizeTransformer",
    "TrainTestSplitter",
    # Nouveaux transformateurs V4
    "DatasetStatistics",
    "ImageComparisonVisualizer",
    "PCAVisualizer",
    "HistogramVisualizer",
]
