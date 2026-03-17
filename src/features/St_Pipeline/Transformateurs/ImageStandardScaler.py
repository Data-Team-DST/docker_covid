"""
ImageStandardScaler - Standardisation d'images.

Transformateur pour standardiser les images pixel-wise (mean=0, std=1).
"""

from typing import Any, Optional
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

try:
    import streamlit as st
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

import matplotlib.pyplot as plt

from .base import BaseTransform


class ImageStandardScaler(BaseTransform):
    """
    Applique un StandardScaler pixel-wise sur les images.
    
    Ce transformateur standardise les images en soustrayant la moyenne
    et en divisant par l'écart-type pour chaque pixel.
    
    Pattern sklearn: Transformation stateful (le scaler doit être fit).
    
    Usage:
        scaler = ImageStandardScaler()
        scaler.fit(X_train)
        X_train_scaled = scaler.transform(X_train)
        X_test_scaled = scaler.transform(X_test)
    """
    
    def __init__(self, **kwargs):
        """
        Initialise le StandardScaler.
        
        Args:
            **kwargs: Paramètres de BaseTransform (verbose, use_streamlit)
        """
        super().__init__(**kwargs)
        self.scaler = StandardScaler()
        self.original_shape_ = None
    
    def _fit(self, X: Any, y: Optional[Any] = None) -> None:
        """
        Apprend les statistiques (moyenne, std) sur les données.
        
        Args:
            X: Images d'entraînement
            y: Labels (unused)
        """
        # Préparer les données
        X_flat, original_shape = self._prepare_data(X, return_shape=True)
        self.original_shape_ = original_shape
        
        self._log(f"Apprentissage StandardScaler sur {X_flat.shape}")
        
        # Fit scaler
        self.scaler.fit(X_flat)
        
        self._log("StandardScaler fitted")
    
    def _process(self, X: Any) -> Any:
        """
        Applique la standardisation aux images.
        
        Args:
            X: Images à transformer
        
        Returns:
            Images standardisées (même format que l'entrée)
        """
        # Préparer les données
        X_flat, original_shape = self._prepare_data(X, return_shape=True)
        
        self._log(f"Standardisation de {X_flat.shape}")
        
        # Sauvegarder stats avant
        X_before_stats = {
            'mean': X_flat.mean(),
            'std': X_flat.std(),
            'min': X_flat.min(),
            'max': X_flat.max()
        }
        
        # Transform avec progress bar
        if self.use_streamlit and self._progress_bar and HAS_STREAMLIT:
            self._update_progress(0, 1, "Standardisation")
            X_scaled = self.scaler.transform(X_flat)
            self._update_progress(1, 1, "Standardisation")
        else:
            X_scaled = self.scaler.transform(X_flat)
        
        # Stats après
        X_after_stats = {
            'mean': X_scaled.mean(),
            'std': X_scaled.std(),
            'min': X_scaled.min(),
            'max': X_scaled.max()
        }
        
        # Visualisation
        self._plot_standardization_effect(X_flat, X_scaled, X_before_stats, X_after_stats)
        
        # Reshape si numpy array (pas DataFrame)
        if not isinstance(X, pd.DataFrame):
            X_scaled = X_scaled.reshape(original_shape)
        
        self._log(f"Standardisation terminée. Shape: {X_scaled.shape}")
        
        return X_scaled
    
    def _prepare_data(self, X: Any, return_shape: bool = False):
        """
        Prépare les données pour StandardScaler (aplatit les images).
        
        Args:
            X: Images (numpy array, liste ou DataFrame)
            return_shape: Si True, retourne aussi la forme originale
        
        Returns:
            Numpy array 2D (n_samples, n_features) et optionnellement la forme
        """
        # Cas 1: DataFrame
        if isinstance(X, pd.DataFrame):
            if 'image_array' not in X.columns:
                raise ValueError("DataFrame doit contenir une colonne 'image_array'")
            
            X_flat = []
            for idx, row in X.iterrows():
                img = row['image_array']
                if img is not None:
                    X_flat.append(img.flatten())
                else:
                    raise ValueError(f"Image None à l'index {idx}")
            
            X_flat = np.array(X_flat)
            
            if return_shape:
                return X_flat, X_flat.shape
            return X_flat
        
        # Cas 2: Numpy array ou liste
        else:
            data_array = np.array(X)
            original_shape = data_array.shape
            n_samples = data_array.shape[0]
            X_flat = data_array.reshape(n_samples, -1)
            
            if return_shape:
                return X_flat, original_shape
            return X_flat
    
    def _plot_standardization_effect(self, X_before, X_after, stats_before, stats_after, n_samples=1000):
        """Visualise effet de la standardisation avec histogrammes."""
        # Échantillonner pour performance
        n = min(len(X_before), n_samples)
        sample_before = X_before[:n].flatten()
        sample_after = X_after[:n].flatten()
        
        if self.use_streamlit and HAS_STREAMLIT:
            st.subheader("📊 Effet de la Standardisation")
            
            # Tableau de statistiques
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Avant:**")
                st.write(f"Mean: {stats_before['mean']:.4f}")
                st.write(f"Std: {stats_before['std']:.4f}")
                st.write(f"Min: {stats_before['min']:.4f}")
                st.write(f"Max: {stats_before['max']:.4f}")
            
            with col2:
                st.markdown("**Après:**")
                st.write(f"Mean: {stats_after['mean']:.4f}")
                st.write(f"Std: {stats_after['std']:.4f}")
                st.write(f"Min: {stats_after['min']:.4f}")
                st.write(f"Max: {stats_after['max']:.4f}")
            
            # Histogrammes comparatifs
            fig = make_subplots(
                rows=1, cols=2,
                subplot_titles=('Distribution Avant', 'Distribution Après')
            )
            
            fig.add_trace(
                go.Histogram(x=sample_before, nbinsx=50, name='Avant'),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Histogram(x=sample_after, nbinsx=50, name='Après'),
                row=1, col=2
            )
            
            fig.update_layout(height=400, showlegend=False)
<<<<<<< HEAD
            st.plotly_chart(fig, use_container_width=True)
=======
            st.plotly_chart(fig, width="stretch")
>>>>>>> origin/Dev
        
        else:
            # Matplotlib
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
            
            ax1.hist(sample_before, bins=50, alpha=0.7, color='blue')
            ax1.set_title('Distribution Avant')
            ax1.set_xlabel('Valeur')
            ax1.set_ylabel('Fréquence')
            ax1.axvline(stats_before['mean'], color='r', linestyle='--', label=f"Mean: {stats_before['mean']:.2f}")
            ax1.legend()
            
            ax2.hist(sample_after, bins=50, alpha=0.7, color='green')
            ax2.set_title('Distribution Après')
            ax2.set_xlabel('Valeur')
            ax2.set_ylabel('Fréquence')
            ax2.axvline(stats_after['mean'], color='r', linestyle='--', label=f"Mean: {stats_after['mean']:.2f}")
            ax2.legend()
            
            plt.tight_layout()
            plt.show()
