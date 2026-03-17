"""
Package de transformateurs pour le pipeline de traitement d'images COVID-19.

Ce package contient tous les transformateurs nécessaires pour charger,
préprocesser, analyser et extraire des features d'images médicales.
"""

from .base import BaseTransform, TransformLogger, UIHandler

# Nouveaux transformateurs V4
from .DatasetStatistics import DatasetStatistics
from .HistogramVisualizer import HistogramVisualizer
from .ImageAnalyser import ImageAnalyser
from .ImageAugmenter import ImageAugmenter
from .ImageComparisonVisualizer import ImageComparisonVisualizer
from .ImageFlattener import ImageFlattener
from .ImageHistogram import ImageHistogram
from .ImageMasker import ImageMasker
from .ImageNormalizer import ImageNormalizer
from .ImagePCA import ImagePCA
from .ImageRandomCropper import ImageRandomCropper
from .ImageResizer import ImageResizer
from .ImageStandardScaler import ImageStandardScaler
from .loaders import ImagePathLoader, TupleToDataFrame
from .PCAVisualizer import PCAVisualizer
from .RGB_to_L import RGB_to_L
from .SaveTransformer import SaveTransformer
from .TrainTestSplitter import TrainTestSplitter
from .VisualizeTransformer import VisualizeTransformer

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
