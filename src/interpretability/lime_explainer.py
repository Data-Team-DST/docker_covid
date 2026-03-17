"""
LIME (Local Interpretable Model-agnostic Explanations) pour images

Explique les prédictions en identifiant les super-pixels importants.
Particulièrement utile pour comprendre quelles régions influencent la classification.

Reference:
    Ribeiro et al. "'Why Should I Trust You?': Explaining the Predictions
    of Any Classifier" (2016)
"""

import warnings
from typing import Callable, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import cv2

try:
    from lime import lime_image
    from lime.wrappers.scikit_image import SegmentationAlgorithm

    LIME_AVAILABLE = True
except ImportError:
    LIME_AVAILABLE = False
    warnings.warn("LIME non installé. Installez avec: pip install lime", ImportWarning)


class LIMEImageExplainer:
    """
    Explainer LIME pour modèles de classification d'images.

    Args:
        predict_fn: Fonction de prédiction du modèle (prend batch, retourne probas)
        segmentation_method: Méthode de segmentation ('quickshift', 'felzenszwalb', 'slic')
        num_samples: Nombre d'échantillons perturbés pour LIME
        batch_size: Taille du batch pour les prédictions

    Example:
        >>> explainer = LIMEImageExplainer(model.predict)
        >>> explanation = explainer.explain_instance(image, top_labels=2)
        >>> explainer.visualize_explanation(image, explanation, label=0)
    """

    def __init__(
        self,
        predict_fn: Callable,
        segmentation_method: str = "quickshift",
        num_samples: int = 1000,
        batch_size: int = 32,
    ):
        if not LIME_AVAILABLE:
            raise ImportError("LIME non installé. Installez avec: pip install lime")

        self.predict_fn = predict_fn
        self.segmentation_method = segmentation_method
        self.num_samples = num_samples
        self.batch_size = batch_size

        # Créer l'explainer LIME
        self.explainer = lime_image.LimeImageExplainer()

    def _mark_boundaries_cv2(self, image: np.ndarray, segments: np.ndarray, color=(1, 1, 0)) -> np.ndarray:
        """
        Marque les frontières des segments en utilisant cv2.
        
        Args:
            image: Image originale (H, W, C) ou (H, W)
            segments: Matrice de segments (H, W) avec labels
            color: Couleur des frontières (RGB, valeurs [0, 1])
        
        Returns:
            Image avec frontières marquées
        """
        # Copier l'image
        marked = image.copy()
        if marked.max() <= 1.0:
            marked = (marked * 255).astype(np.uint8)
        
        # Convertir en couleur si nécessaire
        if len(marked.shape) == 2:
            marked = cv2.cvtColor(marked, cv2.COLOR_GRAY2RGB)
        
        # Trouver les contours de chaque segment
        segments_uint8 = segments.astype(np.uint8)
        unique_labels = np.unique(segments_uint8)
        
        for label in unique_labels:
            mask = (segments_uint8 == label).astype(np.uint8)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(marked, contours, -1, tuple(int(c * 255) for c in color), 1)
        
        # Normaliser à [0, 1]
        return marked.astype(np.float32) / 255.0

    def _get_segmentation_fn(self):
        """Retourne la fonction de segmentation configurée."""
        if self.segmentation_method == "quickshift":
            # Utiliser pyrMeanShiftFiltering comme alternative à quickshift
            def quickshift_cv2(x):
                img = (x * 255).astype(np.uint8) if x.max() <= 1.0 else x.astype(np.uint8)
                if len(img.shape) == 2:
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                shifted = cv2.pyrMeanShiftFiltering(img, 21, 51)
                # Convertir en labels
                gray = cv2.cvtColor(shifted, cv2.COLOR_BGR2GRAY)
                _, labels = cv2.connectedComponents(gray)
                return labels
            return quickshift_cv2
        elif self.segmentation_method == "felzenszwalb":
            # Utiliser pyrMeanShiftFiltering comme alternative
            def felzenszwalb_cv2(x):
                img = (x * 255).astype(np.uint8) if x.max() <= 1.0 else x.astype(np.uint8)
                if len(img.shape) == 2:
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                shifted = cv2.pyrMeanShiftFiltering(img, 21, 51)
                gray = cv2.cvtColor(shifted, cv2.COLOR_BGR2GRAY)
                _, labels = cv2.connectedComponents(gray)
                return labels
            return felzenszwalb_cv2
        elif self.segmentation_method == "slic":
            # Utiliser SLIC de cv2.ximgproc si disponible
            def slic_cv2(x):
                img = (x * 255).astype(np.uint8) if x.max() <= 1.0 else x.astype(np.uint8)
                if len(img.shape) == 2:
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                try:
                    slic_obj = cv2.ximgproc.createSuperpixelSLIC(img, region_size=10)
                    slic_obj.iterate(10)
                    return slic_obj.getLabels()
                except AttributeError:
                    # Fallback si ximgproc n'est pas disponible
                    shifted = cv2.pyrMeanShiftFiltering(img, 21, 51)
                    gray = cv2.cvtColor(shifted, cv2.COLOR_BGR2GRAY)
                    _, labels = cv2.connectedComponents(gray)
                    return labels
            return slic_cv2
        else:
            raise ValueError(f"Méthode inconnue: {self.segmentation_method}")

    def explain_instance(
        self,
        image: np.ndarray,
        top_labels: int = 1,
        hide_color: Optional[int] = None,
        num_features: int = 10,
        random_seed: int = 42,
    ):
        """
        Génère une explication LIME pour une image.

        Args:
            image: Image à expliquer (H, W, C) normalisée [0, 1]
            top_labels: Nombre de classes à expliquer
            hide_color: Couleur pour masquer les segments (None = gris)
            num_features: Nombre de super-pixels à utiliser
            random_seed: Seed pour reproductibilité

        Returns:
            Explication LIME
        """
        # Assurer que l'image est float [0, 1]
        if image.max() > 1:
            image = image / 255.0

        # Générer l'explication
        explanation = self.explainer.explain_instance(
            image,
            self.predict_fn,
            top_labels=top_labels,
            hide_color=hide_color,
            num_samples=self.num_samples,
            batch_size=self.batch_size,
            segmentation_fn=self._get_segmentation_fn(),
            random_seed=random_seed,
        )

        return explanation

    def visualize_explanation(
        self,
        image: np.ndarray,
        explanation,
        label: int,
        positive_only: bool = True,
        num_features: int = 5,
        hide_rest: bool = False,
        figsize: Tuple[int, int] = (15, 5),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        Visualise l'explication LIME.

        Args:
            image: Image originale
            explanation: Objet d'explication LIME
            label: Indice de classe à visualiser
            positive_only: Ne montrer que les contributions positives
            num_features: Nombre de features à afficher
            hide_rest: Masquer les régions non importantes
            figsize: Taille de la figure
            save_path: Chemin de sauvegarde

        Returns:
            Figure matplotlib
        """
        # Obtenir le masque et l'image segmentée
        temp, mask = explanation.get_image_and_mask(
            label,
            positive_only=positive_only,
            num_features=num_features,
            hide_rest=hide_rest,
        )

        # Créer la figure
        fig, axes = plt.subplots(1, 3, figsize=figsize)

        # Image originale
        axes[0].imshow(image)
        axes[0].set_title("Image Originale", fontsize=12, weight="bold")
        axes[0].axis("off")

        # Masque des régions importantes
        axes[1].imshow(mask, cmap="Reds", alpha=0.8)
        axes[1].set_title(
            f"Régions Importantes\n(Top {num_features})", fontsize=12, weight="bold"
        )
        axes[1].axis("off")

        # Explication superposée
        axes[2].imshow(temp)
        axes[2].set_title("LIME Explanation", fontsize=12, weight="bold")
        axes[2].axis("off")

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"✅ Sauvegardé: {save_path}")

        return fig

    def visualize_explanation_boundaries(
        self,
        image: np.ndarray,
        explanation,
        label: int,
        positive_only: bool = True,
        num_features: int = 5,
        figsize: Tuple[int, int] = (12, 5),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        Visualise l'explication avec les frontières des super-pixels.

        Args:
            image: Image originale
            explanation: Explication LIME
            label: Indice de classe
            positive_only: Contributions positives uniquement
            num_features: Nombre de features
            figsize: Taille de la figure
            save_path: Chemin de sauvegarde

        Returns:
            Figure matplotlib
        """
        # Obtenir l'image avec frontières
        temp, mask = explanation.get_image_and_mask(
            label,
            positive_only=positive_only,
            num_features=num_features,
            hide_rest=False,
        )

        # Marquer les frontières avec cv2
        img_boundry = self._mark_boundaries_cv2(temp, mask)

        # Créer la figure
        fig, axes = plt.subplots(1, 2, figsize=figsize)

        # Image originale
        axes[0].imshow(image)
        axes[0].set_title("Image Originale", fontsize=12, weight="bold")
        axes[0].axis("off")

        # Avec frontières
        axes[1].imshow(img_boundry)
        axes[1].set_title(
            f"LIME - Super-pixels\n(Top {num_features})", fontsize=12, weight="bold"
        )
        axes[1].axis("off")

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"✅ Sauvegardé: {save_path}")

        return fig

    def visualize_top_features(
        self,
        explanation,
        label: int,
        num_features: int = 10,
        figsize: Tuple[int, int] = (10, 6),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        Affiche les contributions des top features.

        Args:
            explanation: Explication LIME
            label: Indice de classe
            num_features: Nombre de features à afficher
            figsize: Taille de la figure
            save_path: Chemin de sauvegarde

        Returns:
            Figure matplotlib
        """
        # Obtenir les poids des features
        local_exp = explanation.local_exp[label]

        # Trier par valeur absolue
        sorted_exp = sorted(local_exp, key=lambda x: abs(x[1]), reverse=True)[
            :num_features
        ]

        # Extraire features et poids
        features = [f"Segment {x[0]}" for x in sorted_exp]
        weights = [x[1] for x in sorted_exp]

        # Créer le graphique
        fig, ax = plt.subplots(figsize=figsize)

        colors = ["green" if w > 0 else "red" for w in weights]
        bars = ax.barh(features, weights, color=colors, alpha=0.7)

        ax.set_xlabel("Contribution au Score", fontsize=11)
        ax.set_ylabel("Super-pixel", fontsize=11)
        ax.set_title(
            f"LIME - Top {num_features} Features (Classe {label})",
            fontsize=12,
            weight="bold",
        )
        ax.axvline(x=0, color="black", linestyle="-", linewidth=0.8)
        ax.grid(axis="x", alpha=0.3)

        # Ajouter une légende
        from matplotlib.patches import Patch

        legend_elements = [
            Patch(facecolor="green", alpha=0.7, label="Contribution positive"),
            Patch(facecolor="red", alpha=0.7, label="Contribution négative"),
        ]
        ax.legend(handles=legend_elements, loc="best")

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"✅ Sauvegardé: {save_path}")

        return fig

    def compare_segmentation_methods(
        self,
        image: np.ndarray,
        methods: Optional[List[str]] = None,
        figsize: Tuple[int, int] = (15, 5),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        Compare différentes méthodes de segmentation.

        Args:
            image: Image à segmenter
            methods: Liste de méthodes (None = toutes)
            figsize: Taille de la figure
            save_path: Chemin de sauvegarde

        Returns:
            Figure matplotlib
        """
        if methods is None:
            methods = ["quickshift", "felzenszwalb", "slic"]

        n_methods = len(methods)
        fig, axes = plt.subplots(1, n_methods + 1, figsize=figsize)

        # Image originale
        axes[0].imshow(image)
        axes[0].set_title("Original", fontsize=11, weight="bold")
        axes[0].axis("off")

        # Segmentations
        for i, method in enumerate(methods, 1):
            if method == "quickshift":
                # Utiliser watershed de cv2 comme alternative à quickshift
                gray = cv2.cvtColor(image if len(image.shape) == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2BGR), cv2.COLOR_BGR2GRAY)
                segments = cv2.watershed(image if len(image.shape) == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2BGR), 
                                        cv2.connectedComponents(gray)[1])
            elif method == "felzenszwalb":
                # Utiliser pyrMeanShiftFiltering comme alternative
                segments = cv2.pyrMeanShiftFiltering(image if len(image.shape) == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2BGR), 
                                                     21, 51)[..., 0]
            elif method == "slic":
                # Utiliser SLIC de cv2.ximgproc
                try:
                    slic_obj = cv2.ximgproc.createSuperpixelSLIC(image if len(image.shape) == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2BGR), 
                                                                  region_size=10)
                    slic_obj.iterate(10)
                    segments = slic_obj.getLabels()
                except AttributeError:
                    # Fallback si ximgproc n'est pas disponible
                    segments = cv2.pyrMeanShiftFiltering(image if len(image.shape) == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2BGR), 
                                                         21, 51)[..., 0]

            img_seg = self._mark_boundaries_cv2(image, segments)

            axes[i].imshow(img_seg)
            axes[i].set_title(f"{method.capitalize()}", fontsize=11, weight="bold")
            axes[i].axis("off")

        plt.suptitle(
            "Comparaison des Méthodes de Segmentation", fontsize=13, weight="bold"
        )
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"✅ Sauvegardé: {save_path}")

        return fig

    def explain_batch(
        self,
        images: np.ndarray,
        top_labels: int = 1,
        num_features: int = 5,
        random_seed: int = 42,
    ) -> List:
        """
        Génère des explications pour un batch d'images.

        Args:
            images: Batch d'images (N, H, W, C)
            top_labels: Nombre de classes à expliquer
            num_features: Nombre de features
            random_seed: Seed

        Returns:
            Liste d'explications LIME
        """
        explanations = []
        for i, image in enumerate(images):
            print(f"Explication {i+1}/{len(images)}...", end="\r")
            exp = self.explain_instance(
                image,
                top_labels=top_labels,
                num_features=num_features,
                random_seed=random_seed + i,
            )
            explanations.append(exp)
        print(f"✅ {len(images)} explications générées")
        return explanations


def quick_lime_explanation(
    model,
    image: np.ndarray,
    class_names: List[str],
    label_idx: int = 0,
    num_features: int = 5,
    figsize: Tuple[int, int] = (15, 5),
) -> plt.Figure:
    """
    Fonction rapide pour obtenir une explication LIME.

    Args:
        model: Modèle Keras
        image: Image à expliquer
        class_names: Liste des noms de classe
        label_idx: Indice de classe à expliquer
        num_features: Nombre de features
        figsize: Taille de la figure

    Returns:
        Figure matplotlib

    Example:
        >>> fig = quick_lime_explanation(model, image, ['COVID', 'Normal'], label_idx=0)
        >>> plt.show()
    """
    # Créer l'explainer
    explainer = LIMEImageExplainer(model.predict, num_samples=500)

    # Générer l'explication
    explanation = explainer.explain_instance(
        image, top_labels=1, num_features=num_features
    )

    # Visualiser
    fig = explainer.visualize_explanation(
        image, explanation, label=label_idx, num_features=num_features, figsize=figsize
    )

    # Ajouter le nom de classe au titre
    class_name = (
        class_names[label_idx]
        if label_idx < len(class_names)
        else f"Classe {label_idx}"
    )
    fig.suptitle(f"LIME Explanation - {class_name}", fontsize=13, weight="bold", y=1.02)

    return fig
