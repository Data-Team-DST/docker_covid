"""
Grad-CAM (Gradient-weighted Class Activation Mapping)

Visualise les régions importantes pour la prédiction d'un modèle CNN.
Particulièrement utile pour les images médicales (radiographies COVID-19).

Reference:
    Selvaraju et al. "Grad-CAM: Visual Explanations from Deep Networks
    via Gradient-based Localization" (2017)
"""

from typing import List, Optional, Tuple

import matplotlib.cm as cm
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from tensorflow import keras


class GradCAM:
    """
    Implémentation de Grad-CAM pour TensorFlow/Keras.

    Args:
        model: Modèle Keras compilé
        layer_name: Nom de la couche convolutionnelle à visualiser
                   (par défaut: dernière couche conv)

    Example:
        >>> gradcam = GradCAM(model, layer_name='block5_conv3')
        >>> heatmap = gradcam.compute_heatmap(image, class_idx=0)
        >>> visualize_gradcam(image, heatmap)
    """

    def __init__(self, model: keras.Model, layer_name: Optional[str] = None):
        self.model = model
        self.layer_name = layer_name or self._find_last_conv_layer()

        # Créer un modèle qui renvoie les activations de la couche cible + prédictions
        self.grad_model = self._build_grad_model()

    def _find_last_conv_layer(self) -> str:
        """Trouve automatiquement la dernière couche convolutionnelle."""
        # Parcourir les couches du modèle (ordre inversé)
        for layer in reversed(self.model.layers):
            # Vérifier si c'est une Conv2D par type
            if isinstance(layer, keras.layers.Conv2D):
                return layer.name

            # Vérifier par nom (fallback)
            if "conv" in layer.name.lower():
                return layer.name

            # Si c'est un modèle imbriqué (ex: InceptionV3 dans Sequential)
            if hasattr(layer, "layers"):
                for sublayer in reversed(layer.layers):
                    if isinstance(sublayer, keras.layers.Conv2D):
                        return sublayer.name
                    if "conv" in sublayer.name.lower():
                        return sublayer.name

        raise ValueError("Aucune couche convolutionnelle trouvée dans le modèle")

    def _build_grad_model(self) -> keras.Model:
        """Construit le modèle de gradient."""
        conv_layer = None
        base_model = None

        # Chercher d'abord au niveau du modèle principal
        try:
            conv_layer = self.model.get_layer(self.layer_name)
        except ValueError:
            # Chercher dans les sous-modèles (e.g., InceptionV3 dans Sequential)
            for layer in self.model.layers:
                if hasattr(layer, "get_layer"):
                    try:
                        conv_layer = layer.get_layer(self.layer_name)
                        base_model = layer  # Sauvegarder le modèle de base
                        break
                    except ValueError:
                        continue

        if conv_layer is None:
            raise ValueError(f"Couche '{self.layer_name}' non trouvée dans le modèle")

        # ✅ CORRECTION: Gérer correctement les modèles Sequential
        if isinstance(self.model, keras.Sequential):
            # Pour Sequential, créer un nouveau modèle fonctionnel
            # Obtenir l'input shape de la première couche (SANS accéder à .input ou .input_shape du modèle)
            first_layer = self.model.layers[0]

            # Si la première couche a un input_shape défini (cas de Conv2D avec input_shape)
            if (
                hasattr(first_layer, "input_shape")
                and first_layer.input_shape is not None
            ):
                input_shape = first_layer.input_shape[1:]  # Enlever batch dimension
            elif hasattr(first_layer, "batch_input_shape"):
                input_shape = first_layer.batch_input_shape[1:]
            else:
                # Essayer de construire le modèle pour obtenir l'input shape
                self.model.build()
                input_shape = self.model.input_shape[1:]

            # Créer l'input explicite
            model_input = keras.Input(shape=input_shape)

            # CAS 1: La couche conv est dans un sous-modèle (e.g., InceptionV3 dans Sequential)
            if base_model is not None and conv_layer is not None:
                # Créer un modèle qui extrait à la fois la conv layer et la sortie du base_model
                intermediate_model = keras.Model(
                    inputs=base_model.input,
                    outputs=[conv_layer.output, base_model.output],
                )

                # Reconstruire le forward pass complet
                x = model_input
                conv_output = None

                for layer in self.model.layers:
                    if layer == base_model:
                        # Extraire les deux sorties du base_model
                        conv_output, base_out = intermediate_model(x)
                        x = base_out
                    else:
                        x = layer(x)

                final_output = x

                return keras.Model(
                    inputs=model_input, outputs=[conv_output, final_output]
                )

            # CAS 2: La couche conv est directement dans le Sequential
            else:
                x = model_input
                conv_output = None

                for layer in self.model.layers:
                    x = layer(x)
                    if layer.name == self.layer_name:
                        conv_output = x

                final_output = x  # Sortie finale du modèle

                if conv_output is None:
                    raise ValueError(
                        f"Couche '{self.layer_name}' non atteinte dans le forward pass"
                    )

                return keras.Model(
                    inputs=model_input, outputs=[conv_output, final_output]
                )

        else:
            # Pour les modèles fonctionnels ou avec sous-modèles
            if base_model is not None:
                model_input = base_model.input
            else:
                model_input = self.model.input

            return keras.Model(
                inputs=model_input, outputs=[conv_layer.output, self.model.output]
            )

    def compute_heatmap(
        self, image: np.ndarray, class_idx: Optional[int] = None, normalize: bool = True
    ) -> np.ndarray:
        """
        Calcule la heatmap Grad-CAM pour une image.

        Args:
            image: Image d'entrée (H, W, C) normalisée
            class_idx: Indice de classe (None = classe prédite)
            normalize: Si True, normalise la heatmap entre 0 et 1

        Returns:
            Heatmap Grad-CAM de taille (H, W)
        """
        # Ajouter batch dimension si nécessaire
        if len(image.shape) == 3:
            image = np.expand_dims(image, axis=0)

        # Calculer les gradients
        with tf.GradientTape() as tape:
            conv_outputs, predictions = self.grad_model(image)

            # Utiliser la classe prédite si non spécifiée
            if class_idx is None:
                class_idx = tf.argmax(predictions[0]).numpy()

            # Score de la classe cible
            class_channel = predictions[:, class_idx]

        # Gradients de la classe par rapport aux feature maps
        grads = tape.gradient(class_channel, conv_outputs)

        # Moyenne des gradients sur les dimensions spatiales (Global Average Pooling)
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

        # Pondérer les feature maps par les gradients
        conv_outputs = conv_outputs[0]
        pooled_grads = pooled_grads.numpy()
        conv_outputs = conv_outputs.numpy()

        # Multiplication channel-wise
        for i in range(pooled_grads.shape[-1]):
            conv_outputs[:, :, i] *= pooled_grads[i]

        # Moyenne sur tous les canaux
        heatmap = np.mean(conv_outputs, axis=-1)

        # ReLU - ne garder que les influences positives
        heatmap = np.maximum(heatmap, 0)

        # Normaliser entre 0 et 1
        if normalize and heatmap.max() > 0:
            heatmap = heatmap / heatmap.max()

        return heatmap

    def compute_heatmap_batch(
        self,
        images: np.ndarray,
        class_indices: Optional[List[int]] = None,
        normalize: bool = True,
    ) -> List[np.ndarray]:
        """
        Calcule les heatmaps pour un batch d'images.

        Args:
            images: Batch d'images (N, H, W, C)
            class_indices: Liste des indices de classe (None = classes prédites)
            normalize: Si True, normalise les heatmaps

        Returns:
            Liste de heatmaps
        """
        heatmaps = []
        for i, image in enumerate(images):
            class_idx = class_indices[i] if class_indices else None
            heatmap = self.compute_heatmap(image, class_idx, normalize)
            heatmaps.append(heatmap)
        return heatmaps

    def get_available_layers(self) -> List[str]:
        """Retourne la liste des couches convolutionnelles disponibles."""
        conv_layers = []

        for layer in self.model.layers:
            # Vérifier si c'est une Conv2D par type
            if isinstance(layer, keras.layers.Conv2D):
                conv_layers.append(layer.name)
            # Vérifier par nom (fallback)
            elif "conv" in layer.name.lower():
                conv_layers.append(layer.name)

            # Si c'est un modèle imbriqué (ex: InceptionV3 dans Sequential)
            if hasattr(layer, "layers"):
                for sublayer in layer.layers:
                    if isinstance(sublayer, keras.layers.Conv2D):
                        conv_layers.append(sublayer.name)
                    elif "conv" in sublayer.name.lower():
                        conv_layers.append(sublayer.name)

        return conv_layers


def overlay_heatmap(
    image: np.ndarray, heatmap: np.ndarray, alpha: float = 0.4, colormap: str = "jet"
) -> np.ndarray:
    """
    Superpose la heatmap sur l'image originale.

    Args:
        image: Image originale (H, W, C) normalisée entre 0 et 1
        heatmap: Heatmap Grad-CAM (H, W)
        alpha: Transparence de la heatmap (0-1)
        colormap: Colormap matplotlib ('jet', 'viridis', 'hot', etc.)

    Returns:
        Image avec heatmap superposée (H, W, C)
    """
    # Redimensionner la heatmap à la taille de l'image
    heatmap_resized = (
        tf.image.resize(heatmap[..., np.newaxis], (image.shape[0], image.shape[1]))
        .numpy()
        .squeeze()
    )

    # Appliquer le colormap
    cmap = cm.get_cmap(colormap)
    heatmap_colored = cmap(heatmap_resized)[..., :3]  # Ignorer alpha

    # Assurer que l'image est entre 0 et 1
    if image.max() > 1:
        image = image / 255.0

    # Superposer
    superimposed = heatmap_colored * alpha + image * (1 - alpha)

    return superimposed


def visualize_gradcam(
    image: np.ndarray,
    heatmap: np.ndarray,
    class_name: str = "",
    confidence: Optional[float] = None,
    colormap: str = "jet",
    alpha: float = 0.4,
    figsize: Tuple[int, int] = (15, 5),
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Visualise l'image originale, la heatmap et la superposition.

    Args:
        image: Image originale (H, W, C)
        heatmap: Heatmap Grad-CAM (H, W)
        class_name: Nom de la classe prédite
        confidence: Score de confiance
        colormap: Colormap pour la heatmap
        alpha: Transparence de la superposition
        figsize: Taille de la figure
        save_path: Chemin pour sauvegarder l'image

    Returns:
        Figure matplotlib
    """
    # Créer la superposition
    superimposed = overlay_heatmap(image, heatmap, alpha, colormap)

    # Créer la figure
    fig, axes = plt.subplots(1, 3, figsize=figsize)

    # Image originale
    axes[0].imshow(image, cmap="gray" if image.shape[-1] == 1 else None)
    axes[0].set_title("Image Originale", fontsize=12, weight="bold")
    axes[0].axis("off")

    # Heatmap seule
    im = axes[1].imshow(heatmap, cmap=colormap)
    axes[1].set_title("Grad-CAM Heatmap", fontsize=12, weight="bold")
    axes[1].axis("off")
    plt.colorbar(im, ax=axes[1], fraction=0.046, pad=0.04)

    # Superposition
    axes[2].imshow(superimposed)
    title = "Grad-CAM Overlay"
    if class_name:
        title += f"\nClasse: {class_name}"
    if confidence is not None:
        title += f" ({confidence:.2%})"
    axes[2].set_title(title, fontsize=12, weight="bold")
    axes[2].axis("off")

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"✅ Sauvegardé: {save_path}")

    return fig


def visualize_gradcam_grid(
    images: np.ndarray,
    heatmaps: List[np.ndarray],
    class_names: List[str],
    confidences: Optional[List[float]] = None,
    colormap: str = "jet",
    alpha: float = 0.4,
    n_cols: int = 3,
    figsize: Tuple[int, int] = (18, 6),
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Visualise plusieurs Grad-CAM en grille.

    Args:
        images: Batch d'images (N, H, W, C)
        heatmaps: Liste de heatmaps
        class_names: Liste des noms de classe
        confidences: Liste des scores de confiance
        colormap: Colormap pour les heatmaps
        alpha: Transparence
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
        superimposed = overlay_heatmap(images[i], heatmaps[i], alpha, colormap)

        axes[i].imshow(superimposed)

        title = f"{class_names[i]}"
        if confidences is not None:
            title += f"\n{confidences[i]:.2%}"

        axes[i].set_title(title, fontsize=10, weight="bold")
        axes[i].axis("off")

    # Masquer les axes vides
    for i in range(n_images, len(axes)):
        axes[i].axis("off")

    plt.suptitle("Grad-CAM Visualisations", fontsize=14, weight="bold", y=1.02)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"✅ Sauvegardé: {save_path}")

    return fig


def compare_layers(
    model: keras.Model,
    image: np.ndarray,
    layer_names: Optional[List[str]] = None,
    class_idx: Optional[int] = None,
    colormap: str = "jet",
    figsize: Tuple[int, int] = (18, 6),
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Compare les Grad-CAM de différentes couches convolutionnelles.

    Args:
        model: Modèle Keras
        image: Image à analyser
        layer_names: Liste des couches (None = toutes les conv)
        class_idx: Indice de classe
        colormap: Colormap
        figsize: Taille de la figure
        save_path: Chemin de sauvegarde

    Returns:
        Figure matplotlib
    """
    # Trouver les couches conv si non spécifiées
    if layer_names is None:
        layer_names = []
        for layer in model.layers:
            if "conv" in layer.name.lower():
                layer_names.append(layer.name)

    n_layers = len(layer_names)
    n_cols = min(4, n_layers)
    n_rows = (n_layers + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
    axes = axes.flatten() if n_layers > 1 else [axes]

    for i, layer_name in enumerate(layer_names):
        gradcam = GradCAM(model, layer_name=layer_name)
        heatmap = gradcam.compute_heatmap(image, class_idx=class_idx)
        superimposed = overlay_heatmap(image, heatmap, alpha=0.4, colormap=colormap)

        axes[i].imshow(superimposed)
        axes[i].set_title(f"{layer_name}", fontsize=9, weight="bold")
        axes[i].axis("off")

    # Masquer les axes vides
    for i in range(n_layers, len(axes)):
        axes[i].axis("off")

    plt.suptitle("Grad-CAM - Comparaison des Couches", fontsize=13, weight="bold")
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"✅ Sauvegardé: {save_path}")

    return fig
