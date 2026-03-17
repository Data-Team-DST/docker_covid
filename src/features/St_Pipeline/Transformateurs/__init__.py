"""
Package de transformateurs pour le pipeline de traitement d'images COVID-19.

Ce package contient tous les transformateurs nécessaires pour charger,
préprocesser, analyser et extraire des features d'images médicales.
"""

from .base import BaseTransform, UIHandler, TransformLogger
from .loaders import ImagePathLoader, TupleToDataFrame
from .ImageResizer import ImageResizer
from .ImageAugmenter import ImageAugmenter
from .ImageNormalizer import ImageNormalizer
from .ImageMasker import ImageMasker
from .ImageFlattener import ImageFlattener
from .ImageRandomCropper import ImageRandomCropper
from .ImageStandardScaler import ImageStandardScaler
from .RGB_to_L import RGB_to_L
from .ImageAnalyser import ImageAnalyser
from .ImagePCA import ImagePCA
from .ImageHistogram import ImageHistogram
from .SaveTransformer import SaveTransformer
from .VisualizeTransformer import VisualizeTransformer
from .TrainTestSplitter import TrainTestSplitter

# Nouveaux transformateurs V4
from .DatasetStatistics import DatasetStatistics
from .ImageComparisonVisualizer import ImageComparisonVisualizer
from .PCAVisualizer import PCAVisualizer
from .HistogramVisualizer import HistogramVisualizer

__all__ = [
    # Classes de base
    'BaseTransform',
    'UIHandler', 
    'TransformLogger',
    
    # Loaders
    'ImagePathLoader',
    'TupleToDataFrame',
    
    # Preprocessing
    'ImageResizer',
    'ImageAugmenter',
    'ImageNormalizer',
    'ImageMasker',
    'ImageFlattener',
    'ImageRandomCropper',
    'ImageStandardScaler',
    'RGB_to_L',
    
    # Analyse et features
    'ImageAnalyser',
    'ImagePCA',
    'ImageHistogram',
    
    # Utilities
    'SaveTransformer',
    'VisualizeTransformer',
    'TrainTestSplitter',
    
    # Nouveaux transformateurs V4
    'DatasetStatistics',
    'ImageComparisonVisualizer',
    'PCAVisualizer',
    'HistogramVisualizer',
]
