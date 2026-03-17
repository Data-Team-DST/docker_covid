"""
ImageComparisonVisualizer - Visualise comparaison avant/après transformation.

Transformateur pour afficher des comparaisons visuelles entre images originales
et transformées.
"""

from typing import Any, Optional
import numpy as np
import pandas as pd

try:
    import streamlit as st
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

import matplotlib.pyplot as plt

from .base import BaseTransform


class ImageComparisonVisualizer(BaseTransform):
    """
    Visualise comparaison avant/après transformation de manière générique.
    
    Ce transformateur capture l'état des images avant transformation (fit)
    puis génère des visualisations de comparaison après transformation (transform).
    
    Modes de comparaison:
    - 'side-by-side': Avant à côté d'après
    - 'difference': Avant | Après | Différence absolue
    - 'overlay': Superposition avec transparence
    
    Pattern sklearn: Pass-through (retourne X inchangé).
    
    Attributs:
        n_samples (int): Nombre d'images à afficher
        comparison_mode (str): Mode de visualisation
        X_before_ (Any): Images avant transformation (stockées en fit)
    
    Usage:
        viz = ImageComparisonVisualizer(n_samples=6, comparison_mode='side-by-side')
        viz.fit(X_before)
        X_after = viz.transform(X_after)  # Génère visualisation
    """
    
    def __init__(self, n_samples=6, comparison_mode='side-by-side', **kwargs):
        """
        Initialise le visualisateur de comparaison.
        
        Args:
            n_samples: Nombre d'images à comparer
            comparison_mode: 'side-by-side' | 'difference' | 'overlay'
            **kwargs: BaseTransform parameters
        """
        super().__init__(**kwargs)
        self.n_samples = n_samples
        self.comparison_mode = comparison_mode
        self.X_before_ = None
    
    def _fit(self, X, y=None):
        """
        Stocke les données avant transformation.
        
        Args:
            X: Images avant transformation
            y: Labels (non utilisé)
        """
        # Copier X pour le préserver
        if isinstance(X, pd.DataFrame):
            self.X_before_ = X.copy()
        else:
            self.X_before_ = np.array(X).copy()
        
        self._log(f"Images 'before' capturées: {len(self.X_before_)} échantillons")
    
    def _process(self, X):
        """
        Génère visualisation de comparaison et retourne X inchangé.
        
        Args:
            X: Images après transformation
        
        Returns:
            X inchangé (pass-through)
        """
        if self.X_before_ is None:
            self._log("Aucune donnée 'before' stockée, fit() requis d'abord", level="warning")
            return X
        
        self._plot_comparison(self.X_before_, X)
        
        return X
    
    def _plot_comparison(self, X_before, X_after):
        """
        Génère grille de comparaison.
        
        Args:
            X_before: Images avant
            X_after: Images après
        """
        # Extraire images
        if isinstance(X_before, pd.DataFrame):
            imgs_before = X_before['image_array'].iloc[:self.n_samples].values
            imgs_after = X_after['image_array'].iloc[:self.n_samples].values
        else:
            imgs_before = X_before[:self.n_samples]
            imgs_after = X_after[:self.n_samples]
        
        n = min(len(imgs_before), self.n_samples)
        
        if self.use_streamlit and HAS_STREAMLIT:
            st.subheader("🔄 Comparaison Avant/Après")
            
            if self.comparison_mode == 'side-by-side':
                self._plot_side_by_side_streamlit(imgs_before, imgs_after, n)
            elif self.comparison_mode == 'difference':
                self._plot_difference_streamlit(imgs_before, imgs_after, n)
            elif self.comparison_mode == 'overlay':
                self._plot_overlay_streamlit(imgs_before, imgs_after, n)
        
        else:
            # Matplotlib pour notebooks
            if self.comparison_mode == 'side-by-side':
                self._plot_side_by_side_matplotlib(imgs_before, imgs_after, n)
            elif self.comparison_mode == 'difference':
                self._plot_difference_matplotlib(imgs_before, imgs_after, n)
    
    def _plot_side_by_side_streamlit(self, imgs_before, imgs_after, n):
        """Plotly: 2 lignes × n colonnes."""
        fig = make_subplots(
            rows=2, cols=n,
            subplot_titles=[f"Sample {i+1}" for i in range(n)],
            vertical_spacing=0.05,
            horizontal_spacing=0.02
        )
        
        for i in range(n):
            # Normaliser pour affichage
            img_before = self._prepare_for_display(imgs_before[i])
            img_after = self._prepare_for_display(imgs_after[i])
            
            # Avant (ligne 1)
            fig.add_trace(
                go.Image(z=img_before),
                row=1, col=i+1
            )
            
            # Après (ligne 2)
            fig.add_trace(
                go.Image(z=img_after),
                row=2, col=i+1
            )
        
        fig.update_xaxes(showticklabels=False)
        fig.update_yaxes(showticklabels=False)
        fig.update_layout(
            height=400,
            showlegend=False,
            title_text="Avant (haut) vs Après (bas)"
        )
        
<<<<<<< HEAD
        st.plotly_chart(fig, use_container_width=True)
=======
        st.plotly_chart(fig, width="stretch")
>>>>>>> origin/Dev
    
    def _plot_difference_streamlit(self, imgs_before, imgs_after, n):
        """Plotly: 3 lignes (avant, après, diff)."""
        fig = make_subplots(
            rows=3, cols=n,
            subplot_titles=[f"Sample {i+1}" for i in range(n)],
            vertical_spacing=0.05,
            horizontal_spacing=0.02,
            row_titles=['Avant', 'Après', 'Différence']
        )
        
        for i in range(n):
            img_before = self._prepare_for_display(imgs_before[i])
            img_after = self._prepare_for_display(imgs_after[i])
            
            # Calculer différence absolue
            diff = np.abs(img_after.astype(float) - img_before.astype(float))
            
            # Avant
            fig.add_trace(go.Image(z=img_before), row=1, col=i+1)
            
            # Après
            fig.add_trace(go.Image(z=img_after), row=2, col=i+1)
            
            # Différence (heatmap)
            if len(diff.shape) == 3:
                diff = np.mean(diff, axis=2)  # Moyenne des canaux
            
            fig.add_trace(
                go.Heatmap(z=diff, colorscale='Reds', showscale=(i == n-1)),
                row=3, col=i+1
            )
        
        fig.update_xaxes(showticklabels=False)
        fig.update_yaxes(showticklabels=False)
        fig.update_layout(height=600, showlegend=False, title_text="Comparaison avec Différence")
        
<<<<<<< HEAD
        st.plotly_chart(fig, use_container_width=True)
=======
        st.plotly_chart(fig, width="stretch")
>>>>>>> origin/Dev
    
    def _plot_overlay_streamlit(self, imgs_before, imgs_after, n):
        """Affiche superposition avec slider (simplifié)."""
        st.info("Mode overlay: Affichage côte à côte avec intensités")
        self._plot_side_by_side_streamlit(imgs_before, imgs_after, n)
    
    def _plot_side_by_side_matplotlib(self, imgs_before, imgs_after, n):
        """Matplotlib: 2 lignes × n colonnes."""
        fig, axes = plt.subplots(2, n, figsize=(3*n, 6))
        
        if n == 1:
            axes = axes.reshape(-1, 1)
        
        for i in range(n):
            img_before = self._prepare_for_display(imgs_before[i])
            img_after = self._prepare_for_display(imgs_after[i])
            
            # Avant
            axes[0, i].imshow(img_before, cmap='gray' if len(img_before.shape)==2 else None)
            axes[0, i].set_title('Avant')
            axes[0, i].axis('off')
            
            # Après
            axes[1, i].imshow(img_after, cmap='gray' if len(img_after.shape)==2 else None)
            axes[1, i].set_title('Après')
            axes[1, i].axis('off')
        
        plt.tight_layout()
        plt.show()
    
    def _plot_difference_matplotlib(self, imgs_before, imgs_after, n):
        """Matplotlib: 3 lignes × n colonnes."""
        fig, axes = plt.subplots(3, n, figsize=(3*n, 9))
        
        if n == 1:
            axes = axes.reshape(-1, 1)
        
        for i in range(n):
            img_before = self._prepare_for_display(imgs_before[i])
            img_after = self._prepare_for_display(imgs_after[i])
            diff = np.abs(img_after.astype(float) - img_before.astype(float))
            
            if len(diff.shape) == 3:
                diff = np.mean(diff, axis=2)
            
            # Avant
            axes[0, i].imshow(img_before, cmap='gray' if len(img_before.shape)==2 else None)
            axes[0, i].set_title('Avant')
            axes[0, i].axis('off')
            
            # Après
            axes[1, i].imshow(img_after, cmap='gray' if len(img_after.shape)==2 else None)
            axes[1, i].set_title('Après')
            axes[1, i].axis('off')
            
            # Différence
            im = axes[2, i].imshow(diff, cmap='Reds')
            axes[2, i].set_title('Différence')
            axes[2, i].axis('off')
            
            if i == n-1:
                plt.colorbar(im, ax=axes[2, i])
        
        plt.tight_layout()
        plt.show()
    
    def _prepare_for_display(self, img):
        """
        Prépare image pour affichage (normalise si nécessaire).
        
        Args:
            img: numpy array
        
        Returns:
            Image prête pour affichage
        """
        if img is None:
            return np.zeros((64, 64))
        
        img = np.array(img)
        
        # Normaliser si valeurs > 1
        if img.max() > 1.0:
            img = img / 255.0
        
        # Assurer shape correct pour plotly/matplotlib
        if len(img.shape) == 2:
            # Grayscale 2D
            return img
        elif len(img.shape) == 3:
            if img.shape[2] == 1:
                # Grayscale 3D -> 2D
                return img[:, :, 0]
            else:
                # RGB
                return img
        
        return img
