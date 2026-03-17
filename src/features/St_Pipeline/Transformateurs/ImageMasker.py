"""
ImageMasker - Application de masques binaires.

Transformateur pour appliquer des masques aux images pour isoler les régions d'intérêt.
"""

from typing import Any
import numpy as np
import pandas as pd
from tqdm import tqdm
from PIL import Image

try:
    import streamlit as st
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

import matplotlib.pyplot as plt

from .base import BaseTransform


class ImageMasker(BaseTransform):
    """
    Applique des masques binaires aux images.
    
    Ce transformateur multiplie les images par leurs masques associés pour
    isoler les régions d'intérêt (ROI).
    
    Pattern sklearn: Transformation stateful (les mask_paths sont stockés).
    
    Formats d'entrée supportés:
        - Liste d'images avec mask_paths en paramètre
        - Numpy array avec mask_paths en paramètre
        - DataFrame avec colonnes 'image_array' et 'mask_path'
    
    Usage:
        masker = ImageMasker(mask_paths=mask_list)
        images_masked = masker.fit_transform(images)
        
        # Ou avec DataFrame
        masker = ImageMasker()
        df_masked = masker.fit_transform(df)  # utilise df['mask_path']
    """
    
    def __init__(self, mask_paths=None, **kwargs):
        """
        Initialise le masqueur d'images.
        
        Args:
            mask_paths: Liste des chemins vers les masques (optionnel si DataFrame)
            **kwargs: Paramètres de BaseTransform (verbose, use_streamlit)
        """
        super().__init__(**kwargs)
        self.mask_paths = mask_paths
    
    def _process(self, X: Any) -> Any:
        """
        Applique les masques aux images.
        
        Args:
            X: Liste d'images, numpy array ou DataFrame
        
        Returns:
            Images masquées dans le même format
        
        Raises:
            ValueError: Si mask_paths n'est pas fourni et DataFrame sans 'mask_path'
        """
        # Cas 1: DataFrame avec colonnes 'image_array' et 'mask_path'
        if isinstance(X, pd.DataFrame):
            if 'image_array' not in X.columns or 'mask_path' not in X.columns:
                raise ValueError("DataFrame doit contenir 'image_array' et 'mask_path'")
            
            self._log(f"Application des masques sur {len(X)} images (DataFrame)")
            
            X_transformed = X.copy()
            masked_images = []
            masks_loaded = []
            
            # Dual-mode progress
            if self.use_streamlit and self._progress_bar and HAS_STREAMLIT:
                total = len(X)
                for i, (idx, row) in enumerate(X.iterrows()):
                    self._update_progress(i, total, "Masquage")
                    img = row['image_array']
                    mask_path = row['mask_path']
                    
                    if img is not None and pd.notna(mask_path):
                        masked, mask_arr = self._apply_mask(img, mask_path, return_mask=True)
                        masked_images.append(masked)
                        masks_loaded.append(mask_arr)
                    else:
                        masked_images.append(img)
                        masks_loaded.append(None)
                self._update_progress(total, total, "Masquage")
            else:
                for idx, row in tqdm(X.iterrows(), total=len(X),
                                    desc=f"[{self.__class__.__name__}] Masquage",
                                    disable=not self.verbose):
                    img = row['image_array']
                    mask_path = row['mask_path']
                    
                    if img is not None and pd.notna(mask_path):
                        masked, mask_arr = self._apply_mask(img, mask_path, return_mask=True)
                        masked_images.append(masked)
                        masks_loaded.append(mask_arr)
                    else:
                        masked_images.append(img)
                        masks_loaded.append(None)
            
            X_transformed['image_array'] = masked_images
            
            # Visualisation
            self._plot_masking_effect(X, X_transformed, masks_loaded)
            
            return X_transformed
        
        # Cas 2: Liste ou numpy array avec mask_paths fourni
        else:
            if self.mask_paths is None:
                raise ValueError("mask_paths doit être fourni pour les listes/arrays")
            
            data_array = np.array(X)
            
            if len(data_array) != len(self.mask_paths):
                raise ValueError(
                    f"Nombre d'images ({len(data_array)}) != nombre de masques ({len(self.mask_paths)})"
                )
            
            self._log(f"Application des masques sur {len(data_array)} images")
            
            masked = []
            
            # Dual-mode progress
            if self.use_streamlit and self._progress_bar and HAS_STREAMLIT:
                total = len(data_array)
                for i, (img, mask_path) in enumerate(zip(data_array, self.mask_paths)):
                    self._update_progress(i, total, "Masquage")
                    masked.append(self._apply_mask(img, mask_path))
                self._update_progress(total, total, "Masquage")
            else:
                iterator = zip(data_array, self.mask_paths)
                for img, mask_path in tqdm(iterator, total=len(data_array),
                                          desc=f"[{self.__class__.__name__}] Masquage",
                                          disable=not self.verbose):
                    masked.append(self._apply_mask(img, mask_path))
            
            return np.array(masked)
    
    def _apply_mask(self, image: np.ndarray, mask_path: str, return_mask=False):
        """
        Applique un masque à une image.
        
        Args:
            image: Image à masquer (numpy array)
            mask_path: Chemin vers le masque
            return_mask: Si True, retourne aussi le masque
        
        Returns:
            Image masquée (numpy array) ou (image masquée, masque)
        """
        # Charger le masque
        mask = Image.open(mask_path).convert('L')
        
        # Redimensionner le masque à la taille de l'image
        if len(image.shape) == 3:
            mask = mask.resize((image.shape[1], image.shape[0]))
        else:
            mask = mask.resize((image.shape[1], image.shape[0]))
        
        # Convertir en array binaire
        mask_arr = np.array(mask) > 0
        mask_2d = mask_arr.copy()
        
        # Appliquer le masque
        if len(image.shape) == 3:
            # Image couleur: élargir le masque
            mask_arr = mask_arr[:, :, np.newaxis]
        
        masked_img = image * mask_arr
        
        if return_mask:
            return masked_img, mask_2d
        return masked_img
    
    def _plot_masking_effect(self, X_before, X_after, masks, n_samples=4):
        """Visualise effet masking: original, mask, masked, overlay."""
        if isinstance(X_before, pd.DataFrame):
            imgs_before = X_before['image_array'].iloc[:n_samples].values
            imgs_after = X_after['image_array'].iloc[:n_samples].values
            masks_arr = [m for m in masks[:n_samples] if m is not None]
        else:
            imgs_before = X_before[:n_samples]
            imgs_after = X_after[:n_samples]
            masks_arr = masks[:n_samples]
        
        n = min(len(imgs_before), n_samples)
        
        if self.use_streamlit and HAS_STREAMLIT:
            st.subheader("🎭 Effet du Masquage")
            
            fig = make_subplots(
                rows=4, cols=n,
                subplot_titles=[f"Sample {i+1}" for i in range(n)],
                vertical_spacing=0.03,
                horizontal_spacing=0.02,
                row_titles=['Original', 'Masque', 'Masqué', 'Overlay']
            )
            
            for i in range(n):
                img_orig = self._prepare_for_display(imgs_before[i])
                img_masked = self._prepare_for_display(imgs_after[i])
                mask = masks_arr[i] if i < len(masks_arr) and masks_arr[i] is not None else np.ones_like(img_orig)
                
                # Original
                fig.add_trace(go.Image(z=img_orig), row=1, col=i+1)
                
                # Masque
                fig.add_trace(go.Heatmap(z=mask, colorscale='gray', showscale=False), row=2, col=i+1)
                
                # Masqué
                fig.add_trace(go.Image(z=img_masked), row=3, col=i+1)
                
                # Overlay (original avec contour masque)
                fig.add_trace(go.Image(z=img_orig), row=4, col=i+1)
            
            fig.update_xaxes(showticklabels=False)
            fig.update_yaxes(showticklabels=False)
            fig.update_layout(height=800, showlegend=False)
<<<<<<< HEAD
            st.plotly_chart(fig, use_container_width=True)
=======
            st.plotly_chart(fig, width="stretch")
>>>>>>> origin/Dev
    
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
