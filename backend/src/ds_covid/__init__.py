"""
DS-COVID: COVID-19 Radiography Analysis Package

A comprehensive Python package for analyzing COVID-19 radiography images
using machine learning and deep learning techniques.

Authors:
    - Rafael Cepa <rafael.cepa@cnrs-orleans.fr>
    - Cirine Moire
    - Steven Moire

License: MIT
"""

__version__ = "0.1.0"
__author__ = "Rafael Cepa, Cirine Moire, Steven Moire"
__email__ = "rafael.cepa@cnrs-orleans.fr"
__license__ = "MIT"

# Main package imports - will be populated after creating modules
try:
    from .features import load_images_flat, prepare_covid_data
    from .models import MaskApplicator, build_baseline_cnn, build_cnn
    from .preprocessing import apply_pipeline, process_single_image, squared_crop_to_lungs
    from .segmentation import build_unet, clean_mask
    from .visualization import compare_methods, visualize_samples

    __all__ = [
        "build_baseline_cnn",
        "build_cnn",
        "build_unet",
        "clean_mask",
        "MaskApplicator",
        "load_images_flat",
        "prepare_covid_data",
        "apply_pipeline",
        "process_single_image",
        "squared_crop_to_lungs",
        "visualize_samples",
        "compare_methods",
    ]
except ImportError:
    # During development, modules might not exist yet
    __all__ = []
