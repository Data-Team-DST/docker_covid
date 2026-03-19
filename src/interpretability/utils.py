"""
Utilitaires pour l'interprétabilité des modèles de Deep Learning

Fonctions communes pour:
- Comparaison des différentes méthodes (GradCAM, LIME, SHAP)
- Sauvegarde et chargement des explications
- Visualisations combinées
- Métriques d'évaluation des explications
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np


def plot_multiple_explanations(
    image: np.ndarray,
    gradcam_heatmap: Optional[np.ndarray] = None,
    lime_explanation: Optional[Any] = None,
    shap_values: Optional[np.ndarray] = None,
    class_idx: int = 0,
    class_name: str = "",
    confidence: Optional[float] = None,
    figsize: Tuple[int, int] = (18, 5),
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Compare les 3 méthodes d'interprétabilité côte à côte.

    Args:
        image: Image originale (H, W, C)
        gradcam_heatmap: Heatmap Grad-CAM (H, W)
        lime_explanation: Explication LIME
        shap_values: Valeurs SHAP (H, W, C)
        class_idx: Indice de classe
        class_name: Nom de la classe
        confidence: Score de confiance
        figsize: Taille de la figure
        save_path: Chemin de sauvegarde

    Returns:
        Figure matplotlib

    Example:
        >>> from src.interpretability import GradCAM, LIMEImageExplainer, SHAPExplainer
        >>> gradcam = GradCAM(model)
        >>> heatmap = gradcam.compute_heatmap(image, class_idx=0)
        >>> plot_multiple_explanations(image, gradcam_heatmap=heatmap, class_idx=0)
    """
    import matplotlib.cm as cm

    # Compter le nombre de méthodes disponibles
    methods = []
    if gradcam_heatmap is not None:
        methods.append(("Grad-CAM", gradcam_heatmap))
    if lime_explanation is not None:
        methods.append(("LIME", lime_explanation))
    if shap_values is not None:
        methods.append(("SHAP", shap_values))

    n_methods = len(methods)
    if n_methods == 0:
        raise ValueError("Au moins une méthode d'explication doit être fournie")

    # Créer la figure
    fig, axes = plt.subplots(1, n_methods + 1, figsize=figsize)
    if n_methods + 1 == 1:
        axes = [axes]

    # Image originale
    axes[0].imshow(image, cmap="gray" if image.shape[-1] == 1 else None)
    title = "Image Originale"
    if class_name:
        title += f"\n{class_name}"
    if confidence is not None:
        title += f" ({confidence:.2%})"
    axes[0].set_title(title, fontsize=11, weight="bold")
    axes[0].axis("off")

    # Chaque méthode
    for i, (method_name, explanation) in enumerate(methods, 1):
        if method_name == "Grad-CAM":
            # Superposer Grad-CAM
            from .gradcam import overlay_heatmap

            superimposed = overlay_heatmap(
                image, explanation, alpha=0.4, colormap="jet"
            )
            axes[i].imshow(superimposed)

        elif method_name == "LIME":
            # Visualisation LIME
            temp, mask = explanation.get_image_and_mask(
                class_idx, positive_only=True, num_features=5, hide_rest=False
            )
            axes[i].imshow(temp)

        elif method_name == "SHAP":
            # Visualisation SHAP
            shap_mean = np.mean(np.abs(explanation), axis=-1)
            shap_norm = shap_mean / (shap_mean.max() + 1e-10)

            cmap = cm.get_cmap("jet")
            heatmap_colored = cmap(shap_norm)[..., :3]

            img_display = image.copy()
            if img_display.max() > 1:
                img_display = img_display / 255.0

            superimposed = heatmap_colored * 0.4 + img_display * 0.6
            axes[i].imshow(superimposed)

        axes[i].set_title(method_name, fontsize=11, weight="bold")
        axes[i].axis("off")

    plt.suptitle(
        "Comparaison des Méthodes d'Interprétabilité", fontsize=13, weight="bold"
    )
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"✅ Sauvegardé: {save_path}")

    return fig


def save_explanation(
    explanation_data: Dict[str, Any], save_dir: Path, filename: str, method: str
) -> None:
    """
    Sauvegarde une explication dans un fichier.

    Args:
        explanation_data: Données de l'explication
        save_dir: Dossier de sauvegarde
        filename: Nom du fichier (sans extension)
        method: Méthode utilisée ('gradcam', 'lime', 'shap')

    Example:
        >>> data = {'heatmap': heatmap, 'class_idx': 0, 'confidence': 0.95}
        >>> save_explanation(data, Path('./results'), 'img_001', 'gradcam')
    """
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    filepath = save_dir / f"{filename}_{method}.npz"

    # Sauvegarder les arrays numpy
    np.savez_compressed(filepath, **explanation_data)

    print(f"✅ Explication {method} sauvegardée: {filepath}")


def load_explanation(filepath: Path) -> Dict[str, Any]:
    """
    Charge une explication depuis un fichier.

    Args:
        filepath: Chemin du fichier .npz

    Returns:
        Dictionnaire des données de l'explication

    Example:
        >>> data = load_explanation(Path('./results/img_001_gradcam.npz'))
        >>> heatmap = data['heatmap']
    """
    data = np.load(filepath)
    return {key: data[key] for key in data.files}


def compute_explanation_metrics(
    explanation: np.ndarray, image: np.ndarray, threshold: float = 0.5
) -> Dict[str, float]:
    """
    Calcule des métriques sur une explication.

    Args:
        explanation: Heatmap d'explication (H, W)
        image: Image originale (H, W, C)
        threshold: Seuil pour binariser la heatmap

    Returns:
        Dictionnaire de métriques:
        - coverage: Pourcentage de l'image couvert
        - mean_intensity: Intensité moyenne
        - max_intensity: Intensité maximale
        - concentration: Concentration (entropie inverse)
    """
    # Normaliser l'explication
    exp_norm = explanation / (explanation.max() + 1e-10)

    # Coverage: pourcentage au-dessus du seuil
    coverage = np.mean(exp_norm > threshold)

    # Intensité
    mean_intensity = np.mean(exp_norm)
    max_intensity = np.max(exp_norm)

    # Concentration (mesure d'entropie)
    # Plus c'est concentré, plus la valeur est élevée
    hist, _ = np.histogram(exp_norm, bins=50, range=(0, 1), density=True)
    hist = hist / (hist.sum() + 1e-10)
    entropy = -np.sum(hist * np.log(hist + 1e-10))
    max_entropy = np.log(50)  # Entropie max pour 50 bins
    concentration = 1 - (entropy / max_entropy)

    return {
        "coverage": float(coverage),
        "mean_intensity": float(mean_intensity),
        "max_intensity": float(max_intensity),
        "concentration": float(concentration),
    }


def compare_explanation_metrics(
    gradcam_heatmap: Optional[np.ndarray] = None,
    lime_mask: Optional[np.ndarray] = None,
    shap_heatmap: Optional[np.ndarray] = None,
    image: Optional[np.ndarray] = None,
) -> Dict[str, Dict[str, float]]:
    """
    Compare les métriques des différentes méthodes.

    Args:
        gradcam_heatmap: Heatmap Grad-CAM
        lime_mask: Masque LIME (binaire)
        shap_heatmap: Heatmap SHAP
        image: Image originale

    Returns:
        Dictionnaire de métriques par méthode
    """
    results = {}

    if gradcam_heatmap is not None:
        results["GradCAM"] = compute_explanation_metrics(gradcam_heatmap, image)

    if lime_mask is not None:
        results["LIME"] = compute_explanation_metrics(lime_mask.astype(float), image)

    if shap_heatmap is not None:
        results["SHAP"] = compute_explanation_metrics(shap_heatmap, image)

    return results


def visualize_metrics_comparison(
    metrics: Dict[str, Dict[str, float]],
    figsize: Tuple[int, int] = (12, 8),
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Visualise la comparaison des métriques sous forme de barres.

    Args:
        metrics: Dictionnaire de métriques par méthode
        figsize: Taille de la figure
        save_path: Chemin de sauvegarde

    Returns:
        Figure matplotlib
    """
    methods = list(metrics.keys())
    metric_names = list(metrics[methods[0]].keys())

    n_metrics = len(metric_names)
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    axes = axes.flatten()

    colors = {"GradCAM": "#FF6B6B", "LIME": "#4ECDC4", "SHAP": "#45B7D1"}

    for i, metric_name in enumerate(metric_names):
        values = [metrics[method][metric_name] for method in methods]

        bars = axes[i].bar(
            methods,
            values,
            color=[colors.get(m, "#95a5a6") for m in methods],
            alpha=0.8,
        )

        axes[i].set_ylabel("Valeur", fontsize=10)
        axes[i].set_title(
            metric_name.replace("_", " ").title(), fontsize=11, weight="bold"
        )
        axes[i].grid(axis="y", alpha=0.3)

        # Ajouter les valeurs au-dessus des barres
        for bar in bars:
            height = bar.get_height()
            axes[i].text(
                bar.get_x() + bar.get_width() / 2,
                height,
                f"{height:.3f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    plt.suptitle(
        "Comparaison des Métriques d'Interprétabilité", fontsize=13, weight="bold"
    )
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"✅ Sauvegardé: {save_path}")

    return fig


def batch_explain(
    images: np.ndarray,
    model,
    method: str = "gradcam",
    layer_name: Optional[str] = None,
    background_data: Optional[np.ndarray] = None,
    class_indices: Optional[List[int]] = None,
    verbose: bool = True,
) -> List[np.ndarray]:
    """
    Génère des explications pour un batch d'images.

    Args:
        images: Batch d'images (N, H, W, C)
        model: Modèle Keras
        method: 'gradcam', 'lime', ou 'shap'
        layer_name: Nom de la couche (pour GradCAM)
        background_data: Données de référence (pour SHAP)
        class_indices: Indices des classes (None = prédites)
        verbose: Afficher la progression

    Returns:
        Liste d'explications
    """
    explanations = []

    if method == "gradcam":
        from .gradcam import GradCAM

        gradcam = GradCAM(model, layer_name=layer_name)

        for i, image in enumerate(images):
            if verbose:
                print(f"Grad-CAM {i+1}/{len(images)}", end="\r")

            class_idx = class_indices[i] if class_indices else None
            heatmap = gradcam.compute_heatmap(image, class_idx=class_idx)
            explanations.append(heatmap)

    elif method == "lime":
        from .lime_explainer import LIMEImageExplainer

        explainer = LIMEImageExplainer(model.predict)
        explanations = explainer.explain_batch(images)

    elif method == "shap":
        from .shap_explainer import SHAPExplainer

        if background_data is None:
            raise ValueError("background_data requis pour SHAP")

        explainer = SHAPExplainer(model, background_data)
        shap_values = explainer.explain(images)

        # Extraire les heatmaps pour chaque image
        for i in range(len(images)):
            class_idx = class_indices[i] if class_indices else 0
            heatmap = np.mean(np.abs(shap_values[class_idx][i]), axis=-1)
            explanations.append(heatmap)

    else:
        raise ValueError(f"Méthode inconnue: {method}")

    if verbose:
        print(f"✅ {len(explanations)} explications générées ({method})")

    return explanations


def create_interpretation_report(
    image: np.ndarray,
    model,
    class_names: List[str],
    true_label: int,
    pred_label: int,
    confidence: float,
    save_dir: Path,
    filename_prefix: str = "report",
    include_lime: bool = True,
    include_shap: bool = True,
    background_data: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Génère un rapport complet d'interprétabilité pour une image.

    Args:
        image: Image à analyser
        model: Modèle Keras
        class_names: Liste des noms de classe
        true_label: Label véritable
        pred_label: Label prédit
        confidence: Confiance de la prédiction
        save_dir: Dossier de sauvegarde
        filename_prefix: Préfixe des fichiers
        include_lime: Inclure LIME
        include_shap: Inclure SHAP
        background_data: Données de référence (pour SHAP)

    Returns:
        Dictionnaire contenant toutes les explications et métriques
    """
    from .gradcam import GradCAM

    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "true_label": int(true_label),
        "pred_label": int(pred_label),
        "true_class": class_names[true_label],
        "pred_class": class_names[pred_label],
        "confidence": float(confidence),
        "correct": true_label == pred_label,
    }

    # Grad-CAM
    print("Génération Grad-CAM...")
    gradcam = GradCAM(model)
    gradcam_heatmap = gradcam.compute_heatmap(image, class_idx=pred_label)
    report["gradcam_heatmap"] = gradcam_heatmap

    # LIME
    lime_explanation = None
    if include_lime:
        print("Génération LIME...")
        from .lime_explainer import LIMEImageExplainer

        lime_explainer = LIMEImageExplainer(model.predict, num_samples=500)
        lime_explanation = lime_explainer.explain_instance(image, top_labels=1)
        report["lime_explanation"] = lime_explanation

    # SHAP
    shap_values = None
    if include_shap:
        if background_data is None:
            print("⚠️ SHAP ignoré: background_data non fourni")
        else:
            print("Génération SHAP...")
            from .shap_explainer import SHAPExplainer

            shap_explainer = SHAPExplainer(model, background_data)
            shap_values = shap_explainer.explain(image[np.newaxis, ...])[0]
            report["shap_values"] = shap_values[pred_label]

    # Visualisation comparative
    print("Création de la visualisation comparative...")
    fig = plot_multiple_explanations(
        image,
        gradcam_heatmap=gradcam_heatmap,
        lime_explanation=lime_explanation,
        shap_values=shap_values[pred_label] if shap_values is not None else None,
        class_idx=pred_label,
        class_name=class_names[pred_label],
        confidence=confidence,
        save_path=save_dir / f"{filename_prefix}_comparison.png",
    )
    plt.close(fig)

    # Sauvegarder les données
    save_explanation(
        {"heatmap": gradcam_heatmap, "class_idx": pred_label},
        save_dir,
        filename_prefix,
        "gradcam",
    )

    # Sauvegarder le rapport JSON
    report_json = {
        "true_label": report["true_label"],
        "pred_label": report["pred_label"],
        "true_class": report["true_class"],
        "pred_class": report["pred_class"],
        "confidence": report["confidence"],
        "correct": report["correct"],
    }

    with open(save_dir / f"{filename_prefix}_report.json", "w") as f:
        json.dump(report_json, f, indent=2)

    print(f"✅ Rapport complet sauvegardé dans {save_dir}")

    return report
