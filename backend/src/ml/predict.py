"""Pipeline de prédiction — inférence sur features extraites."""

import numpy as np


def predict_from_features(model, features: np.ndarray) -> np.ndarray:
    """Prédit les labels pour un tableau de features.

    Args:
        model: Modèle sklearn entraîné.
        features: Tableau numpy (n_samples, n_features).

    Returns:
        Tableau de labels prédits.
    """
    return model.predict(features)


def predict_proba_from_features(model, features: np.ndarray):
    """Retourne les probabilités si le modèle le supporte.

    Args:
        model: Modèle sklearn entraîné.
        features: Tableau numpy (n_samples, n_features).

    Returns:
        Tableau de probabilités ou None si non supporté.
    """
    if hasattr(model, "predict_proba"):
        return model.predict_proba(features)
    return None
