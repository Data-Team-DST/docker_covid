"""
ImageRandomCropper - Crop aléatoire d'images.

Transformateur pour effectuer un crop aléatoire sur les images.
"""

from typing import Any, Optional
import random
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


class ImageRandomCropper(BaseTransform):
    """
    Effectue un crop aléatoire sur chaque image.
    
    Ce transformateur extrait une région rectangulaire aléatoire de chaque image.
    Utile pour l'augmentation de données et l'entraînement de modèles.
    
    Pattern sklearn: Transformation stateless avec seed pour reproductibilité.
    
    Usage:
        cropper = ImageRandomCropper(crop_size=(224, 224), seed=42)
        images_cropped = cropper.fit_transform(images)
    """
    
    def __init__(self, crop_size=(224, 224), seed=None, **kwargs):
        """
        Initialise le cropper aléatoire.
        
        Args:
            crop_size: Tuple (height, width) pour la taille du crop
            seed: Graine pour reproductibilité
            **kwargs: Paramètres de BaseTransform (verbose, use_streamlit)
        """
        super().__init__(**kwargs)
        self.crop_size = crop_size
        self.seed = seed
        self.rng_ = None
        self.crop_positions_ = []
    
    def _fit(self, X: Any, y: Optional[Any] = None) -> None:
        """
        Initialise le générateur de nombres aléatoires.
        
        Args:
            X: Données (unused)
            y: Labels (unused)
        """
        if self.seed is not None:
            random.seed(self.seed)
            np.random.seed(self.seed)
        self.rng_ = random
    
    def _process(self, X: Any) -> Any:
        """
        Applique le random crop aux images.
        
        Args:
            X: Images à cropper
        
        Returns:
            Images croppées
        """
        if self.rng_ is None:
            self._fit(X)
        
        # Cas 1: DataFrame
        if isinstance(X, pd.DataFrame):
            if 'image_array' not in X.columns:
                raise ValueError("DataFrame doit contenir une colonne 'image_array'")
            
            self._log(f"Random crop de {len(X)} images en {self.crop_size}")
            
            X_transformed = X.copy()
            cropped_images = []
            self.crop_positions_ = []
            
            # Dual-mode progress
            if self.use_streamlit and self._progress_bar and HAS_STREAMLIT:
                total = len(X)
                for i, (idx, row) in enumerate(X.iterrows()):
                    self._update_progress(i, total, "RandomCrop")
                    img = row['image_array']
                    if img is not None:
                        cropped_images.append(self._crop_image(img))
                    else:
                        cropped_images.append(None)
                self._update_progress(total, total, "RandomCrop")
            else:
                for idx, row in tqdm(X.iterrows(), total=len(X),
                                    desc=f"[{self.__class__.__name__}] RandomCrop",
                                    disable=not self.verbose):
                    img = row['image_array']
                    if img is not None:
                        cropped_images.append(self._crop_image(img))
                    else:
                        cropped_images.append(None)
            
            X_transformed['image_array'] = cropped_images
            
            # Visualisation
            self._plot_crop_positions()
            
            return X_transformed
        
        # Cas 2: Liste ou numpy array
        else:
            data_array = np.array(X)
            self._log(f"Random crop de {len(data_array)} images")
            
            cropped = []
            self.crop_positions_ = []
            
            # Dual-mode progress
            if self.use_streamlit and self._progress_bar and HAS_STREAMLIT:
                total = len(data_array)
                for i, img in enumerate(data_array):
                    self._update_progress(i, total, "RandomCrop")
                    cropped.append(self._crop_image(img))
                self._update_progress(total, total, "RandomCrop")
            else:
                for img in tqdm(data_array, desc=f"[{self.__class__.__name__}] RandomCrop",
                               disable=not self.verbose):
                    cropped.append(self._crop_image(img))
            
            result = np.array(cropped)
            self._log(f"Random crop terminé. Shape: {result.shape}")
            
            # Visualisation
            self._plot_crop_positions()
            
            return result
    
    def _crop_image(self, img: np.ndarray) -> np.ndarray:
        """
        Crop une seule image aléatoirement.
        
        Args:
            img: Image à cropper (numpy array)
        
        Returns:
            Image croppée (numpy array)
        """
        h, w = img.shape[:2]
        ch, cw = self.crop_size
        
        # Si l'image est plus petite que le crop, la retourner telle quelle
        if h < ch or w < cw:
            self._log(f"Image trop petite ({h}x{w}) pour crop ({ch}x{cw}), ignoré", level="warning")
            return img
        
        # Position aléatoire du crop
        top = random.randint(0, h - ch)
        left = random.randint(0, w - cw)
        
        # Tracker position (pour visualisation)
        self.crop_positions_.append((top, left, h, w))
        
        # Crop
        return img[top:top+ch, left:left+cw]
    
    def _plot_crop_positions(self, n_samples=50):
        """Visualise heatmap des positions de crop."""
        if not self.crop_positions_:
            return
        
        # Extraire positions
        positions = np.array(self.crop_positions_[:n_samples])
        if len(positions) == 0:
            return
        
        tops = positions[:, 0]
        lefts = positions[:, 1]
        h_avg = int(positions[:, 2].mean())
        w_avg = int(positions[:, 3].mean())
        
        # Créer heatmap
        heatmap = np.zeros((h_avg, w_avg))
        ch, cw = self.crop_size
        
        for top, left, _, _ in positions:
            if top + ch <= h_avg and left + cw <= w_avg:
                heatmap[int(top):int(top+ch), int(left):int(left+cw)] += 1
        
        if self.use_streamlit and HAS_STREAMLIT:
            st.subheader("🎯 Heatmap Positions de Crop")
            
            fig = go.Figure(data=go.Heatmap(
                z=heatmap,
                colorscale='Hot',
                colorbar=dict(title='Fréquence')
            ))
            
            fig.update_layout(
                title=f"Positions de crop (taille: {self.crop_size})",
                xaxis_title="Width",
                yaxis_title="Height",
                height=500
            )
            
<<<<<<< HEAD
            st.plotly_chart(fig, use_container_width=True)
=======
            st.plotly_chart(fig, width="stretch")
>>>>>>> origin/Dev
            st.info(f"Analyse de {len(positions)} crops")
