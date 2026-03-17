"""
ImageAugmenter - Augmentation d'images.

Transformateur pour appliquer des augmentations aléatoires aux images
(flips, rotation, bruit, brightness, zoom).
"""

from typing import Any, Optional
import numpy as np
import pandas as pd
from tqdm import tqdm

try:
    import streamlit as st
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

import matplotlib.pyplot as plt

from .base import BaseTransform


class ImageAugmenter(BaseTransform):
    """
    Applique une augmentation d'images (flips, rotation, bruit, brightness, zoom).
    
    Ce transformateur applique des transformations aléatoires aux images pour
    augmenter la diversité du dataset et améliorer la généralisation du modèle.
    
    Pattern sklearn: Transformation stateless avec seed pour reproductibilité.
    
    Transformations disponibles:
        - Flips horizontal/vertical
        - Rotation aléatoire
        - Ajustement de luminosité
        - Bruit gaussien
        - Zoom aléatoire
    
    Usage:
        augmenter = ImageAugmenter(
            flip_horizontal=True,
            rotation_range=15,
            probability=0.5,
            seed=42
        )
        images_aug = augmenter.fit_transform(images)
    """
    
    def __init__(self, 
                 flip_horizontal=True,
                 flip_vertical=False,
                 rotation_range=0,
                 brightness_range=None,
                 noise_std=0.0,
                 zoom_range=None,
                 probability=0.5,
                 seed=None,
                 **kwargs):
        """
        Initialise l'augmentateur d'images.
        
        Args:
            flip_horizontal: Active le flip horizontal
            flip_vertical: Active le flip vertical
            rotation_range: Angle maximum de rotation (degrés)
            brightness_range: Tuple (min, max) pour ajustement de luminosité
            noise_std: Écart-type du bruit gaussien
            zoom_range: Tuple (min, max) pour le facteur de zoom
            probability: Probabilité d'appliquer l'augmentation à chaque image
            seed: Graine pour reproductibilité
            **kwargs: Paramètres de BaseTransform (verbose, use_streamlit)
        """
        super().__init__(**kwargs)
        self.flip_horizontal = flip_horizontal
        self.flip_vertical = flip_vertical
        self.rotation_range = rotation_range
        
        # Convertir brightness_range en tuple si nécessaire
        if brightness_range is not None and not isinstance(brightness_range, (tuple, list)):
            # Si float/int, interpréter comme facteur max : range = (1-val, 1+val)
            self.brightness_range = (1.0 - brightness_range, 1.0 + brightness_range)
        else:
            self.brightness_range = brightness_range
        
        self.noise_std = noise_std
        
        # Convertir zoom_range en tuple si nécessaire
        if zoom_range is not None and not isinstance(zoom_range, (tuple, list)):
            # Si float/int, interpréter comme facteur max : range = (1-val, 1+val)
            self.zoom_range = (1.0 - zoom_range, 1.0 + zoom_range)
        else:
            self.zoom_range = zoom_range
        
        self.probability = probability
        self.seed = seed
        self.rng_ = None
        self.n_images_augmented_ = 0
    
    def _fit(self, X: Any, y: Optional[Any] = None) -> None:
        """
        Initialise le générateur de nombres aléatoires.
        
        Args:
            X: Données (unused)
            y: Labels (unused)
        """
        self.rng_ = np.random.default_rng(self.seed)
    
    def _process(self, X: Any) -> Any:
        """
        Applique l'augmentation aux images.
        
        Args:
            X: Liste d'images, numpy array ou DataFrame
        
        Returns:
            Images augmentées dans le même format
        """
        if self.rng_ is None:
            self._fit(X)
        
        # Cas 1: DataFrame
        if isinstance(X, pd.DataFrame):
            if 'image_array' not in X.columns:
                raise ValueError("DataFrame doit contenir une colonne 'image_array'")
            
            self._log(f"Augmentation de {len(X)} images (p={self.probability}) (DataFrame)")
            
            X_transformed = X.copy()
            aug_images = []
            n_augmented = 0
            
            # Dual-mode progress
            if self.use_streamlit and self._progress_bar and HAS_STREAMLIT:
                iterator = enumerate(X.iterrows())
                total = len(X)
                for i, (idx, row) in iterator:
                    self._update_progress(i, total, "Augmentation")
                    img = row['image_array']
                    if img is not None and self.rng_.random() < self.probability:
                        aug_images.append(self._augment_image(img))
                        n_augmented += 1
                    else:
                        aug_images.append(img)
                self._update_progress(total, total, "Augmentation")
            else:
                for idx, row in tqdm(X.iterrows(), total=len(X),
                                    desc=f"[{self.__class__.__name__}] Augmentation",
                                    disable=not self.verbose):
                    img = row['image_array']
                    if img is not None and self.rng_.random() < self.probability:
                        aug_images.append(self._augment_image(img))
                        n_augmented += 1
                    else:
                        aug_images.append(img)
            
            X_transformed['image_array'] = aug_images
            self.n_images_augmented_ = n_augmented
            
            # Visualisation après transformation
            self._plot_augmentation_comparison(X, X_transformed)
            
            if self.verbose:
                self._log(f"Augmentation terminée: {n_augmented}/{len(X)} images augmentées")
            
            return X_transformed
        
        # Cas 2: Liste ou numpy array
        else:
            data_array = np.array(X)
            self._log(f"Augmentation de {len(data_array)} images (p={self.probability})")
            
            data_aug = []
            n_augmented = 0
            
            # Dual-mode progress
            if self.use_streamlit and self._progress_bar and HAS_STREAMLIT:
                total = len(data_array)
                for i, img in enumerate(data_array):
                    self._update_progress(i, total, "Augmentation")
                    if self.rng_.random() < self.probability:
                        data_aug.append(self._augment_image(img))
                        n_augmented += 1
                    else:
                        data_aug.append(img)
                self._update_progress(total, total, "Augmentation")
            else:
                iterator = tqdm(data_array, desc=f"[{self.__class__.__name__}] Augmentation",
                               disable=not self.verbose)
                for img in iterator:
                    if self.rng_.random() < self.probability:
                        data_aug.append(self._augment_image(img))
                        n_augmented += 1
                    else:
                        data_aug.append(img)
            
            self.n_images_augmented_ = n_augmented
            
            if self.verbose:
                self._log(f"Augmentation terminée: {n_augmented}/{len(data_array)} images augmentées")
            
            return np.array(data_aug)
    
    def _augment_image(self, img: np.ndarray) -> np.ndarray:
        """
        Applique les transformations aléatoires à une image.
        
        Args:
            img: Image à augmenter (numpy array)
        
        Returns:
            Image augmentée (numpy array)
        """
        img_aug = img.copy()
        target_shape = img.shape
        
        # Flip horizontal
        if self.flip_horizontal and self.rng_.random() > 0.5:
            img_aug = np.fliplr(img_aug)
        
        # Flip vertical
        if self.flip_vertical and self.rng_.random() > 0.5:
            img_aug = np.flipud(img_aug)
        
        # Rotation
        if self.rotation_range > 0:
            angle = self.rng_.uniform(-self.rotation_range, self.rotation_range)
            from scipy import ndimage
            img_aug = ndimage.rotate(img_aug, angle, reshape=False, mode='nearest')
        
        # Brightness
        if self.brightness_range is not None:
            factor = self.rng_.uniform(self.brightness_range[0], self.brightness_range[1])
            img_aug = np.clip(img_aug * factor, 0, 255 if img_aug.max() > 1 else 1)
        
        # Noise
        if self.noise_std > 0:
            noise = self.rng_.normal(0, self.noise_std, img_aug.shape)
            img_aug = np.clip(img_aug + noise, 0, 255 if img_aug.max() > 1 else 1)
        
        # Zoom
        if self.zoom_range is not None:
            import cv2
            zoom_factor = self.rng_.uniform(self.zoom_range[0], self.zoom_range[1])
            h, w = img_aug.shape[:2]
            new_h, new_w = int(h * zoom_factor), int(w * zoom_factor)
            
            if zoom_factor != 1.0:
                # Redimensionner
                img_zoomed = cv2.resize(img_aug, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                
                # Padding ou crop pour revenir à la taille originale
                if zoom_factor > 1.0:
                    # Crop au centre
                    start_h = (new_h - h) // 2
                    start_w = (new_w - w) // 2
                    img_aug = img_zoomed[start_h:start_h+h, start_w:start_w+w]
                else:
                    # Pad
                    pad_h = (h - new_h) // 2
                    pad_w = (w - new_w) // 2
                    if len(img_aug.shape) == 3:
                        npad = ((pad_h, h - new_h - pad_h), (pad_w, w - new_w - pad_w), (0, 0))
                    else:
                        npad = ((pad_h, h - new_h - pad_h), (pad_w, w - new_w - pad_w))
                    img_aug = np.pad(img_zoomed, npad, mode='constant')
        
        # S'assurer que la forme est préservée
        if img_aug.shape != target_shape:
            import cv2
            if len(target_shape) == 3:
                img_aug = cv2.resize(img_aug, (target_shape[1], target_shape[0]), interpolation=cv2.INTER_LINEAR)
            else:
                img_aug = cv2.resize(img_aug, (target_shape[1], target_shape[0]), interpolation=cv2.INTER_LINEAR)
        
        return img_aug.astype(img.dtype)
    
    def _plot_augmentation_comparison(self, X_before, X_after, n_samples=6):
        """Visualise comparaison avant/après augmentation."""
        if isinstance(X_before, pd.DataFrame):
            imgs_before = X_before['image_array'].iloc[:n_samples].values
            imgs_after = X_after['image_array'].iloc[:n_samples].values
        else:
            imgs_before = X_before[:n_samples]
            imgs_after = X_after[:n_samples]
        
        n = min(len(imgs_before), n_samples)
        
        if self.use_streamlit and HAS_STREAMLIT:
            st.subheader("🎲 Comparaison Augmentation")
            
            fig = make_subplots(
                rows=2, cols=n,
                subplot_titles=[f"Sample {i+1}" for i in range(n)],
                vertical_spacing=0.05,
                horizontal_spacing=0.02
            )
            
            for i in range(n):
                img_before = self._prepare_for_display(imgs_before[i])
                img_after = self._prepare_for_display(imgs_after[i])
                
                fig.add_trace(go.Image(z=img_before), row=1, col=i+1)
                fig.add_trace(go.Image(z=img_after), row=2, col=i+1)
            
            fig.update_xaxes(showticklabels=False)
            fig.update_yaxes(showticklabels=False)
            fig.update_layout(height=400, showlegend=False, title_text="Avant (haut) vs Après (bas)")
<<<<<<< HEAD
            st.plotly_chart(fig, use_container_width=True)
=======
            st.plotly_chart(fig, width="stretch")
>>>>>>> origin/Dev
            
            st.info(f"Augmenté: {self.n_images_augmented_}/{len(X_before)} images (p={self.probability})")
    
    def _prepare_for_display(self, img):
        """Prépare image pour affichage."""
        if img is None:
            return np.zeros((64, 64))
        img = np.array(img)
        if img.max() > 1.0:
            img = img / 255.0
        if len(img.shape) == 2:
            return img
        elif len(img.shape) == 3 and img.shape[2] == 1:
            return img[:, :, 0]
        return img
    
    def visualize(self, X_before: Any, X_after: Any, n_samples: int = 3) -> None:
        """Visualise les effets de l'augmentation."""
        import matplotlib.pyplot as plt
        
        # Extraire les images
        if isinstance(X_before, pd.DataFrame):
            images_before = [X_before['image_array'].iloc[i] for i in range(min(n_samples, len(X_before)))]
            images_after = [X_after['image_array'].iloc[i] for i in range(min(n_samples, len(X_after)))]
        else:
            images_before = X_before[:n_samples]
            images_after = X_after[:n_samples]
        
        fig, axes = plt.subplots(2, n_samples, figsize=(4*n_samples, 8))
        fig.suptitle(f'ImageAugmenter: Augmentations aléatoires (p={self.probability})', fontsize=16, fontweight='bold')
        
        for i in range(n_samples):
            # Avant
            axes[0, i].imshow(images_before[i], cmap='gray' if len(images_before[i].shape)==2 else None)
            axes[0, i].set_title(f'Original')
            axes[0, i].axis('off')
            
            # Après
            axes[1, i].imshow(images_after[i], cmap='gray' if len(images_after[i].shape)==2 else None)
            axes[1, i].set_title(f'Augmenté')
            axes[1, i].axis('off')
        
        plt.tight_layout()
        plt.show()
        
        # Statistiques
        print(f"\n📊 Statistiques d'augmentation:")
        print(f"   - Probabilité: {self.probability}")
        print(f"   - Rotation max: ±{self.rotation_range}°")
        print(f"   - Images augmentées: {self.n_images_augmented_}/{len(images_before) if images_before else 0}")
