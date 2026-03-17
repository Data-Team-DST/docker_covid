"""
SHAP (SHapley Additive exPlanations) pour Deep Learning

Utilise les valeurs de Shapley pour expliquer les prédictions des modèles CNN.
Fournit une explication globale et locale des contributions de chaque pixel.

Reference:
    Lundberg & Lee "A Unified Approach to Interpreting Model Predictions" (2017)
"""

import warnings
from typing import List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np

try:
    import shap

    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    warnings.warn("SHAP non installé. Installez avec: pip install shap", ImportWarning)


class SHAPExplainer:
    """
    Explainer SHAP pour modèles de Deep Learning (CNN).

    Utilise DeepExplainer pour les modèles TensorFlow/Keras.

    Args:
        model: Modèle Keras compilé
        background_data: Données de référence pour SHAP (subset du training set)
                        Taille recommandée: 50-100 images
        layer: Couche du modèle à analyser (None = sortie finale)

    Example:
        >>> explainer = SHAPExplainer(model, X_train[:100])
        >>> shap_values = explainer.explain(X_test[:10])
        >>> explainer.visualize_image_plot(X_test[0], shap_values[0], class_idx=0)
    """

    def __init__(self, model, background_data: np.ndarray, layer: Optional[int] = None):
        if not SHAP_AVAILABLE:
            raise ImportError("SHAP non installé. Installez avec: pip install shap")

        self.model = model
        self.background_data = background_data
        self.layer = layer

        # Créer l'explainer DeepExplainer
        self.explainer = shap.DeepExplainer(model, background_data)

    def explain(self, images: np.ndarray, check_additivity: bool = False) -> np.ndarray:
        """
        Calcule les valeurs SHAP pour un batch d'images.

        Args:
            images: Images à expliquer (N, H, W, C)
            check_additivity: Vérifier l'additivité (plus lent)

        Returns:
            Valeurs SHAP de forme (N, H, W, C, num_classes)
        """
        print(f"Calcul des valeurs SHAP pour {len(images)} images...")

        shap_values = self.explainer.shap_values(
            images, check_additivity=check_additivity
        )

        print("✅ Valeurs SHAP calculées")
        return shap_values

    def visualize_image_plot(
        self,
        image: np.ndarray,
        shap_values: np.ndarray,
        class_idx: int,
        class_name: str = "",
        figsize: Tuple[int, int] = (12, 4),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        Visualise les valeurs SHAP pour une image et une classe.

        Args:
            image: Image originale (H, W, C)
            shap_values: Valeurs SHAP pour cette image (H, W, C)
            class_idx: Indice de classe
            class_name: Nom de la classe
            figsize: Taille de la figure
            save_path: Chemin de sauvegarde

        Returns:
            Figure matplotlib
        """
        # Créer la figure
        fig, axes = plt.subplots(1, 3, figsize=figsize)

        # Image originale
        axes[0].imshow(image, cmap="gray" if image.shape[-1] == 1 else None)
        axes[0].set_title("Image Originale", fontsize=11, weight="bold")
        axes[0].axis("off")

        # Valeurs SHAP moyennées sur les canaux
        shap_mean = np.mean(np.abs(shap_values[class_idx]), axis=-1)

        im1 = axes[1].imshow(shap_mean, cmap="Reds")
        axes[1].set_title("SHAP Values\n(Magnitude)", fontsize=11, weight="bold")
        axes[1].axis("off")
        plt.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

        # Valeurs SHAP signées (pos/neg)
        shap_signed = np.mean(shap_values[class_idx], axis=-1)

        im2 = axes[2].imshow(
            shap_signed,
            cmap="RdBu_r",
            vmin=-np.abs(shap_signed).max(),
            vmax=np.abs(shap_signed).max(),
        )
        axes[2].set_title("SHAP Values\n(Signed)", fontsize=11, weight="bold")
        axes[2].axis("off")
        plt.colorbar(im2, ax=axes[2], fraction=0.046, pad=0.04)

        title = "SHAP Explanation"
        if class_name:
            title += f" - {class_name}"
        else:
            title += f" - Classe {class_idx}"

        plt.suptitle(title, fontsize=12, weight="bold")
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"✅ Sauvegardé: {save_path}")

        return fig

    def visualize_heatmap(
        self,
        image: np.ndarray,
        shap_values: np.ndarray,
        class_idx: int,
        alpha: float = 0.4,
        colormap: str = "jet",
        figsize: Tuple[int, int] = (12, 4),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        Superpose les valeurs SHAP sur l'image originale.

        Args:
            image: Image originale
            shap_values: Valeurs SHAP
            class_idx: Indice de classe
            alpha: Transparence de la heatmap
            colormap: Colormap matplotlib
            figsize: Taille de la figure
            save_path: Chemin de sauvegarde

        Returns:
            Figure matplotlib
        """
        import matplotlib.cm as cm

        # Calculer la heatmap
        shap_mean = np.mean(np.abs(shap_values[class_idx]), axis=-1)
        shap_norm = shap_mean / (shap_mean.max() + 1e-10)

        # Appliquer le colormap
        cmap = cm.get_cmap(colormap)
        heatmap_colored = cmap(shap_norm)[..., :3]

        # Normaliser l'image
        img_display = image.copy()
        if img_display.max() > 1:
            img_display = img_display / 255.0

        # Superposer
        superimposed = heatmap_colored * alpha + img_display * (1 - alpha)

        # Créer la figure
        fig, axes = plt.subplots(1, 3, figsize=figsize)

        axes[0].imshow(image, cmap="gray" if image.shape[-1] == 1 else None)
        axes[0].set_title("Original", fontsize=11, weight="bold")
        axes[0].axis("off")

        axes[1].imshow(shap_norm, cmap=colormap)
        axes[1].set_title("SHAP Heatmap", fontsize=11, weight="bold")
        axes[1].axis("off")

        axes[2].imshow(superimposed)
        axes[2].set_title("Overlay", fontsize=11, weight="bold")
        axes[2].axis("off")

        plt.suptitle(f"SHAP Heatmap - Classe {class_idx}", fontsize=12, weight="bold")
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"✅ Sauvegardé: {save_path}")

        return fig

    def visualize_summary_plot(
        self,
        images: np.ndarray,
        shap_values: List[np.ndarray],
        class_names: List[str],
        max_display: int = 20,
        figsize: Tuple[int, int] = (12, 8),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        Crée un summary plot SHAP pour visualiser l'importance globale.

        Args:
            images: Images analysées
            shap_values: Liste de valeurs SHAP par classe
            class_names: Noms des classes
            max_display: Nombre max de features à afficher
            figsize: Taille de la figure
            save_path: Chemin de sauvegarde

        Returns:
            Figure matplotlib
        """
        # Aplatir les images et shap_values pour le summary plot
        n_samples = len(images)
        n_features = np.prod(images.shape[1:])

        images_flat = images.reshape(n_samples, -1)

        # Prendre la première classe pour le summary
        shap_flat = shap_values[0].reshape(n_samples, -1)

        # Créer le plot
        fig = plt.figure(figsize=figsize)
        shap.summary_plot(shap_flat, images_flat, max_display=max_display, show=False)

        plt.title("SHAP Summary Plot", fontsize=12, weight="bold", pad=20)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"✅ Sauvegardé: {save_path}")

        return fig

    def visualize_force_plot(
        self,
        image: np.ndarray,
        shap_values: np.ndarray,
        class_idx: int,
        class_name: str = "",
    ):
        """
        Crée un force plot interactif SHAP.

        Args:
            image: Image originale
            shap_values: Valeurs SHAP
            class_idx: Indice de classe
            class_name: Nom de la classe

        Returns:
            Force plot SHAP (objet HTML)

        Note:
            Fonctionne mieux dans Jupyter notebooks
        """
        # Aplatir l'image et les shap values
        image_flat = image.flatten()
        shap_flat = shap_values[class_idx].flatten()

        # Prédiction de base (moyenne sur background)
        base_value = self.explainer.expected_value[class_idx]

        # Créer le force plot
        force_plot = shap.force_plot(
            base_value, shap_flat, image_flat, matplotlib=False
        )

        return force_plot

    def visualize_decision_plot(
        self,
        shap_values: List[np.ndarray],
        class_idx: int,
        class_name: str = "",
        figsize: Tuple[int, int] = (10, 6),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        Crée un decision plot montrant comment SHAP arrive à la prédiction.

        Args:
            shap_values: Valeurs SHAP
            class_idx: Indice de classe
            class_name: Nom de la classe
            figsize: Taille de la figure
            save_path: Chemin de sauvegarde

        Returns:
            Figure matplotlib
        """
        # Aplatir les shap values
        shap_flat = shap_values[class_idx].reshape(len(shap_values[class_idx]), -1)

        # Expected value
        base_value = self.explainer.expected_value[class_idx]

        # Créer le plot
        fig = plt.figure(figsize=figsize)
        shap.decision_plot(base_value, shap_flat, show=False)

        title = "SHAP Decision Plot"
        if class_name:
            title += f" - {class_name}"
        plt.title(title, fontsize=12, weight="bold")
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"✅ Sauvegardé: {save_path}")

        return fig

    def compare_classes(
        self,
        image: np.ndarray,
        shap_values: List[np.ndarray],
        class_names: List[str],
        figsize: Tuple[int, int] = (16, 4),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        Compare les valeurs SHAP pour toutes les classes.

        Args:
            image: Image originale
            shap_values: Liste de valeurs SHAP par classe
            class_names: Noms des classes
            figsize: Taille de la figure
            save_path: Chemin de sauvegarde

        Returns:
            Figure matplotlib
        """
        n_classes = len(class_names)
        fig, axes = plt.subplots(1, n_classes + 1, figsize=figsize)

        # Image originale
        axes[0].imshow(image, cmap="gray" if image.shape[-1] == 1 else None)
        axes[0].set_title("Original", fontsize=10, weight="bold")
        axes[0].axis("off")

        # Heatmap pour chaque classe
        for i, class_name in enumerate(class_names):
            shap_mean = np.mean(np.abs(shap_values[i]), axis=-1)

            im = axes[i + 1].imshow(shap_mean, cmap="Reds")
            axes[i + 1].set_title(f"{class_name}", fontsize=10, weight="bold")
            axes[i + 1].axis("off")

        plt.suptitle(
            "SHAP Values - Comparaison des Classes", fontsize=12, weight="bold"
        )
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"✅ Sauvegardé: {save_path}")

        return fig

    def visualize_grid(
        self,
        images: np.ndarray,
        shap_values_list: List[List[np.ndarray]],
        class_indices: List[int],
        class_names: List[str],
        n_cols: int = 3,
        figsize: Tuple[int, int] = (15, 10),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        Visualise plusieurs images avec leurs SHAP values en grille.

        Args:
            images: Batch d'images
            shap_values_list: Liste de valeurs SHAP
            class_indices: Indices des classes à visualiser
            class_names: Noms des classes
            n_cols: Nombre de colonnes
            figsize: Taille de la figure
            save_path: Chemin de sauvegarde

        Returns:
            Figure matplotlib
        """
        n_images = len(images)
        n_rows = (n_images + n_cols - 1) // n_cols

        fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
        axes = axes.flatten() if n_images > 1 else [axes]

        for i in range(n_images):
            shap_values = shap_values_list[i]
            class_idx = class_indices[i]

            # Calculer la heatmap
            shap_mean = np.mean(np.abs(shap_values[class_idx]), axis=-1)

            # Superposer sur l'image
            img_display = images[i].copy()
            if img_display.max() > 1:
                img_display = img_display / 255.0

            # Normaliser et coloriser
            import matplotlib.cm as cm

            shap_norm = shap_mean / (shap_mean.max() + 1e-10)
            cmap = cm.get_cmap("jet")
            heatmap_colored = cmap(shap_norm)[..., :3]

            superimposed = heatmap_colored * 0.4 + img_display * 0.6

            axes[i].imshow(superimposed)
            axes[i].set_title(f"{class_names[class_idx]}", fontsize=10, weight="bold")
            axes[i].axis("off")

        # Masquer les axes vides
        for i in range(n_images, len(axes)):
            axes[i].axis("off")

        plt.suptitle("SHAP Explanations", fontsize=13, weight="bold")
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"✅ Sauvegardé: {save_path}")

        return fig


def quick_shap_explanation(
    model,
    background_data: np.ndarray,
    image: np.ndarray,
    class_names: List[str],
    class_idx: int = 0,
    figsize: Tuple[int, int] = (12, 4),
) -> plt.Figure:
    """
    Fonction rapide pour obtenir une explication SHAP.

    Args:
        model: Modèle Keras
        background_data: Données de référence (50-100 images)
        image: Image à expliquer
        class_names: Liste des noms de classe
        class_idx: Indice de classe
        figsize: Taille de la figure

    Returns:
        Figure matplotlib

    Example:
        >>> fig = quick_shap_explanation(model, X_train[:100], X_test[0],
        ...                               ['COVID', 'Normal'], class_idx=0)
        >>> plt.show()
    """
    # Créer l'explainer
    explainer = SHAPExplainer(model, background_data)

    # Calculer les valeurs SHAP
    shap_values = explainer.explain(image[np.newaxis, ...])

    # Visualiser
    class_name = (
        class_names[class_idx]
        if class_idx < len(class_names)
        else f"Classe {class_idx}"
    )
    fig = explainer.visualize_image_plot(
        image, shap_values[0], class_idx, class_name=class_name, figsize=figsize
    )

    return fig
