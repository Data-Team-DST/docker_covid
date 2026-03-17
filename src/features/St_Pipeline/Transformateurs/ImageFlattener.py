"""
ImageFlattener - Aplatissement d'images en vecteurs 1D.

Transformateur pour convertir des images 2D/3D en vecteurs 1D.
"""

from typing import Any
import numpy as np
import pandas as pd
from tqdm import tqdm

try:
    import streamlit as st
    import plotly.graph_objects as go
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

from .base import BaseTransform


class ImageFlattener(BaseTransform):
    """
    Aplatit les images en vecteurs 1D.
    
    Ce transformateur convertit des images 2D ou 3D en vecteurs 1D,
    nécessaire pour l'utilisation avec certains algorithmes ML traditionnels.
    
    Pattern sklearn: Transformation stateless (sans apprentissage).
    
    Formats d'entrée supportés:
        - Numpy array 3D/4D (grayscale/color images)
        - DataFrame avec colonne 'image_array'
    
    Sortie:
        - Numpy array 2D (n_samples, n_features)
        - DataFrame avec colonne 'image_array' mise à jour
    
    Usage:
        flattener = ImageFlattener()
        X_flat = flattener.fit_transform(images)  # Shape: (n_samples, height*width*channels)
    """
    
    def _process(self, X: Any) -> Any:
        """
        Aplatit les images en vecteurs 1D.
        
        Args:
            X: Numpy array ou DataFrame
        
        Returns:
            Images aplaties (2D array ou DataFrame)
        """
        # Cas 1: DataFrame
        if isinstance(X, pd.DataFrame):
            if 'image_array' not in X.columns:
                raise ValueError("DataFrame doit contenir une colonne 'image_array'")
            
            self._log(f"Aplatissement de {len(X)} images (DataFrame)")
            
            X_transformed = X.copy()
            flat_images = []
            total = len(X)
            
            if self.use_streamlit and self._progress_bar is not None:
                # Mode Streamlit
                for idx, (_, row) in enumerate(X.iterrows()):
                    img = row['image_array']
                    if img is not None:
                        flat_images.append(img.flatten())
                    else:
                        flat_images.append(None)
                    
                    if idx % 100 == 0 or idx == total - 1:
                        progress = (idx + 1) / total
                        self._update_progress(progress, f"Aplati {idx + 1}/{total}")
                self._clear_progress()
            else:
                # Mode console avec tqdm
                for idx, row in tqdm(X.iterrows(), total=total,
                                    desc=f"[{self.__class__.__name__}] Aplatissement",
                                    disable=not self.verbose):
                    img = row['image_array']
                    if img is not None:
                        flat_images.append(img.flatten())
                    else:
                        flat_images.append(None)
            
            X_transformed['image_array'] = flat_images
            
            return X_transformed
        
        # Cas 2: Numpy array
        else:
            data_array = np.array(X)
            n_samples = data_array.shape[0]
            
            self._log(f"Aplatissement de {n_samples} images de shape {data_array.shape}")
            
            # Aplatir en conservant la première dimension (n_samples)
            X_flat = []
            for img in tqdm(data_array, desc=f"[{self.__class__.__name__}] Aplatissement",
                           disable=not self.verbose):
                X_flat.append(img.flatten())
            
            X_flat = np.array(X_flat)
            
            self._log(f"Aplatissement terminé. Shape: {X_flat.shape}")
            
            # Visualisation en mode Streamlit
            if self.use_streamlit:
                self._plot_flattening_stats(data_array, X_flat)
            
            return X_flat
    
    def _plot_flattening_stats(self, X_before, X_after):
        """Visualise les statistiques du flattening."""
        if self.use_streamlit and HAS_STREAMLIT:
            st.markdown("### 📦 Statistiques d'Aplatissement")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Shape Avant", str(X_before.shape))
            with col2:
                st.metric("Shape Après", str(X_after.shape))
            with col3:
                compression = (X_before.size - X_after.size) / X_before.size * 100
                st.metric("Features", f"{X_after.shape[1]:,}")
            
            # Visualiser distributions features
            st.markdown("**Distribution des features (premiers 1000)**")
            sample_features = X_after[0, :min(1000, X_after.shape[1])]
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=sample_features, mode='lines', name='Features'))
            fig.update_layout(xaxis_title="Index", yaxis_title="Valeur", height=300)
<<<<<<< HEAD
            st.plotly_chart(fig, use_container_width=True)
=======
            st.plotly_chart(fig, width="stretch")
>>>>>>> origin/Dev
