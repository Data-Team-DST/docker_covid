"""DS COVID - COVID-19 Radiography Analysis Package.

A comprehensive package for analyzing COVID-19 radiographic
images using deep learning.
"""

__version__ = "0.1.0"
__author__ = "Rafael Cepa, Cirine, Steven Moire"
__email__ = "rafael.cepa@example.fr"

__all__ = [
    "features",
    "__version__",
]

# Lazy import to avoid circular imports
try:
    import importlib

    for module in ["explorationdata", "features", "models", "streamlit"]:
        importlib.import_module(f"{__name__}.{module}")
except ImportError:
    pass
