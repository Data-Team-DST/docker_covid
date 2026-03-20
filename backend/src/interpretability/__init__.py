"""
Module d'interprétabilité pour les modèles de Deep Learning

Ce module fournit des outils pour comprendre les décisions des modèles CNN:
- GradCAM: Visualisation des zones d'attention
- LIME: Explication par segmentation d'image
- SHAP: Valeurs de Shapley pour deep learning
"""

from .gradcam import GradCAM, visualize_gradcam
from .lime_explainer import LIMEImageExplainer
from .shap_explainer import SHAPExplainer
from .utils import (
    create_interpretation_report,
    plot_multiple_explanations,
    save_explanation,
)

__all__ = [
    "GradCAM",
    "visualize_gradcam",
    "LIMEImageExplainer",
    "SHAPExplainer",
    "plot_multiple_explanations",
    "save_explanation",
    "create_interpretation_report",
]
