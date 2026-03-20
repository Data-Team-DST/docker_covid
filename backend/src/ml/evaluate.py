"""Évaluation des modèles ML — métriques de classification."""

import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


def compute_metrics(y_true, y_pred, class_names=None):
    """Retourne accuracy, rapport et matrice de confusion.

    Args:
        y_true: Labels réels.
        y_pred: Labels prédits.
        class_names: Noms des classes (optionnel).

    Returns:
        dict avec accuracy (float), report (str), confusion_matrix (list).
    """
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "report": classification_report(
            y_true, y_pred, target_names=class_names, zero_division=0
        ),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }


def top_class(probas, class_names):
    """Retourne la classe avec la probabilité la plus haute.

    Args:
        probas: Tableau de probabilités.
        class_names: Liste des noms de classes.

    Returns:
        Tuple (nom_classe, confiance).
    """
    idx = int(np.argmax(probas))
    return class_names[idx], float(probas[idx])
