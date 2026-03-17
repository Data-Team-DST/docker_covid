"""
HistogramVisualizer - Visualise distributions d'histogrammes par classe.

Transformateur pour afficher distributions d'histogrammes calculés,
avec comparaisons entre classes et heatmaps.
"""

from typing import Any, Optional
import numpy as np
import pandas as pd

try:
    import streamlit as st
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

import matplotlib.pyplot as plt

from .base import BaseTransform


class HistogramVisualizer(BaseTransform):
    """
    Visualise distributions d'histogrammes d'intensité par classe.
    
    Ce transformateur attend des histogrammes calculés (n_samples × n_bins)
    et génère visualisations comparatives:
    - Moyennes par classe
    - Overlay de distributions
    - Heatmap d'histogrammes
    
    Pattern sklearn: Pass-through (retourne X inchangé).
    
    Attributs:
        n_bins (int): Nombre de bins attendus
        plot_mode (str): 'mean' | 'overlay' | 'heatmap' | 'all'
        n_samples_display (int): Nombre d'échantillons pour heatmap
    
    Usage:
        viz = HistogramVisualizer(n_bins=32, plot_mode='all')
        viz.fit(X_hist, y)
        X_hist = viz.transform(X_hist)  # Génère visualisation
    """
    
    def __init__(self, n_bins=32, plot_mode='all', n_samples_display=50, **kwargs):
        """
        Initialise le visualisateur d'histogrammes.
        
        Args:
            n_bins: Nombre de bins attendus
            plot_mode: 'mean' | 'overlay' | 'heatmap' | 'all'
            n_samples_display: Nombre d'échantillons pour heatmap
            **kwargs: BaseTransform parameters
        """
        super().__init__(**kwargs)
        self.n_bins = n_bins
        self.plot_mode = plot_mode
        self.n_samples_display = n_samples_display
        self.class_means_ = {}
    
    def _fit(self, X, y=None):
        """
        Calcule moyennes d'histogrammes par classe.
        
        Args:
            X: Histogrammes (n_samples, n_bins)
            y: Labels (optionnel)
        """
        if y is None:
            self._log("Aucun label fourni, visualisation limitée", level="warning")
            return
        
        # Extraire histogrammes
        if isinstance(X, pd.DataFrame):
            X_hist = X.drop(columns=['label'], errors='ignore').values
            if 'label' in X.columns:
                y = X['label'].values
        else:
            X_hist = np.array(X)
        
        # Calculer moyennes par classe
        classes = np.unique(y)
        for cls in classes:
            mask = (y == cls)
            self.class_means_[cls] = X_hist[mask].mean(axis=0)
        
        self._log(f"Moyennes calculées pour {len(classes)} classes")
    
    def _process(self, X):
        """
        Génère visualisations et retourne X inchangé.
        
        Args:
            X: Histogrammes
        
        Returns:
            X inchangé (pass-through)
        """
        # Extraire labels si présents
        y = None
        if isinstance(X, pd.DataFrame):
            if 'label' in X.columns:
                y = X['label'].values
                X_hist = X.drop(columns=['label']).values
            else:
                X_hist = X.values
        else:
            X_hist = np.array(X)
        
        if self.plot_mode in ['mean', 'all']:
            self._plot_class_means(X_hist, y)
        
        if self.plot_mode in ['overlay', 'all']:
            self._plot_overlay(X_hist, y)
        
        if self.plot_mode in ['heatmap', 'all']:
            self._plot_heatmap(X_hist, y)
        
        return X
    
    def _plot_class_means(self, X_hist, y):
        """
        Graphique moyennes d'histogrammes par classe.
        
        Args:
            X_hist: Histogrammes
            y: Labels
        """
        if not self.class_means_:
            self._log("Moyennes non calculées, fit() requis", level="warning")
            return
        
        bins = np.arange(self.n_bins)
        
        if self.use_streamlit and HAS_STREAMLIT:
            st.subheader("📊 Moyennes d'Histogrammes par Classe")
            
            fig = go.Figure()
            
            for cls, mean_hist in self.class_means_.items():
                fig.add_trace(go.Scatter(
                    x=bins, y=mean_hist,
                    mode='lines+markers',
                    name=str(cls),
                    line=dict(width=2)
                ))
            
            fig.update_layout(
                xaxis_title='Bin',
                yaxis_title='Fréquence Moyenne',
                title='Distribution Moyenne par Classe',
                height=400
            )
            
            st.plotly_chart(fig, width="stretch")
        
        else:
            # Matplotlib
            plt.figure(figsize=(12, 6))
            
            for cls, mean_hist in self.class_means_.items():
                plt.plot(bins, mean_hist, marker='o', label=cls, linewidth=2)
            
            plt.xlabel('Bin')
            plt.ylabel('Fréquence Moyenne')
            plt.title('Distribution Moyenne par Classe')
            plt.legend()
            plt.grid(alpha=0.3)
            plt.tight_layout()
            plt.show()
    
    def _plot_overlay(self, X_hist, y):
        """
        Overlay de plusieurs histogrammes par classe.
        
        Args:
            X_hist: Histogrammes
            y: Labels
        """
        if y is None:
            return
        
        bins = np.arange(self.n_bins)
        classes = np.unique(y)
        n_per_class = 5  # Afficher 5 échantillons par classe
        
        if self.use_streamlit and HAS_STREAMLIT:
            st.subheader("🎨 Overlay d'Histogrammes")
            
            fig = go.Figure()
            
            for cls in classes:
                mask = (y == cls)
                samples = X_hist[mask][:n_per_class]
                
                for i, sample in enumerate(samples):
                    fig.add_trace(go.Scatter(
                        x=bins, y=sample,
                        mode='lines',
                        name=f"{cls} - {i+1}",
                        line=dict(width=1),
                        opacity=0.5
                    ))
            
            fig.update_layout(
                xaxis_title='Bin',
                yaxis_title='Fréquence',
                title=f'Overlay de {n_per_class} échantillons par classe',
                height=500,
                showlegend=True
            )
            
            st.plotly_chart(fig, width="stretch")
        
        else:
            # Matplotlib
            fig, axes = plt.subplots(1, len(classes), figsize=(5*len(classes), 5))
            
            if len(classes) == 1:
                axes = [axes]
            
            for idx, cls in enumerate(classes):
                mask = (y == cls)
                samples = X_hist[mask][:n_per_class]
                
                for sample in samples:
                    axes[idx].plot(bins, sample, alpha=0.5, linewidth=1)
                
                axes[idx].set_title(f'Classe: {cls}')
                axes[idx].set_xlabel('Bin')
                axes[idx].set_ylabel('Fréquence')
                axes[idx].grid(alpha=0.3)
            
            plt.tight_layout()
            plt.show()
    
    def _plot_heatmap(self, X_hist, y):
        """
        Heatmap d'histogrammes (échantillons × bins).
        
        Args:
            X_hist: Histogrammes
            y: Labels
        """
        n = min(len(X_hist), self.n_samples_display)
        
        if self.use_streamlit and HAS_STREAMLIT:
            st.subheader("🔥 Heatmap d'Histogrammes")
            
            # Trier par classe pour meilleure visualisation
            if y is not None:
                indices = np.argsort(y)[:n]
                X_sorted = X_hist[indices]
                y_sorted = y[indices]
            else:
                X_sorted = X_hist[:n]
                y_sorted = None
            
            fig = go.Figure(data=go.Heatmap(
                z=X_sorted,
                colorscale='Viridis',
                colorbar=dict(title='Fréquence')
            ))
            
            fig.update_layout(
                xaxis_title='Bin',
                yaxis_title='Échantillon',
                title=f'Heatmap de {n} Histogrammes',
                height=600
            )
            
            st.plotly_chart(fig, width="stretch")
            
            if y_sorted is not None:
                # Afficher distribution des classes
                st.info(f"Classes présentes: {', '.join(map(str, np.unique(y_sorted)))}")
        
        else:
            # Matplotlib
            plt.figure(figsize=(12, 8))
            
            if y is not None:
                indices = np.argsort(y)[:n]
                X_sorted = X_hist[indices]
            else:
                X_sorted = X_hist[:n]
            
            plt.imshow(X_sorted, aspect='auto', cmap='viridis', interpolation='nearest')
            plt.colorbar(label='Fréquence')
            plt.xlabel('Bin')
            plt.ylabel('Échantillon')
            plt.title(f'Heatmap de {n} Histogrammes')
            plt.tight_layout()
            plt.show()
