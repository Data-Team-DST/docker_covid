"""
ImageHistogram - Extraction d'histogrammes d'intensité.

Transformateur pour calculer les histogrammes d'intensité des images.
"""

from typing import Any
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

from .base import BaseTransform


class ImageHistogram(BaseTransform):
    """
    Calcule l'histogramme d'intensité pour chaque image.
    
    Ce transformateur extrait la distribution des intensités de pixels
    sous forme d'histogramme, créant ainsi un vecteur de features.
    
    Pattern sklearn: Transformation stateless (sans apprentissage).
    
    Usage:
        histogram = ImageHistogram(bins=32)
        features = histogram.fit_transform(images)  # Shape: (n_samples, bins)
    """
    
    def __init__(self, bins=32, **kwargs):
        """
        Initialise l'extracteur d'histogrammes.
        
        Args:
            bins: Nombre de bins pour l'histogramme
            **kwargs: Paramètres de BaseTransform (verbose, use_streamlit)
        """
        super().__init__(**kwargs)
        self.bins = bins
    
    def _process(self, X: Any) -> Any:
        """
        Calcule les histogrammes des images.
        
        Args:
            X: Images (numpy array, liste ou DataFrame)
        
        Returns:
            Numpy array 2D (n_samples, bins) avec les histogrammes
        """
        # Cas 1: DataFrame
        if isinstance(X, pd.DataFrame):
            if 'image_array' not in X.columns:
                raise ValueError("DataFrame doit contenir une colonne 'image_array'")
            
            self._log(f"Calcul des histogrammes ({self.bins} bins) pour {len(X)} images")
            
            histos = []
            total = len(X)
            
            if self.use_streamlit and self._progress_bar is not None:
                # Mode Streamlit
                for idx, (_, row) in enumerate(X.iterrows()):
                    img = row['image_array']
                    if img is not None:
                        histo = np.histogram(img.flatten(), bins=self.bins, range=(0, 1))[0]
                        histos.append(histo)
                    else:
                        histos.append(np.zeros(self.bins))
                    
                    if idx % 100 == 0 or idx == total - 1:
                        progress = (idx + 1) / total
                        self._update_progress(progress, f"Histogramme {idx + 1}/{total}")
                self._clear_progress()
            else:
                # Mode console avec tqdm
                for idx, row in tqdm(X.iterrows(), total=total,
                                    desc=f"[{self.__class__.__name__}] Histogrammes",
                                    disable=not self.verbose):
                    img = row['image_array']
                    if img is not None:
                        histo = np.histogram(img.flatten(), bins=self.bins, range=(0, 1))[0]
                        histos.append(histo)
                    else:
                        histos.append(np.zeros(self.bins))
            
            histos_array = np.array(histos)
            
            # Visualisation en mode Streamlit
            if self.use_streamlit:
                self._plot_histogram_features(X['image_array'].tolist()[:4], histos_array[:4])
            
            return histos_array
        
        # Cas 2: Numpy array ou liste
        else:
            data_array = np.array(X)
            self._log(f"Calcul des histogrammes ({self.bins} bins)")
            
            histos = []
            for img in tqdm(data_array, desc=f"[{self.__class__.__name__}] Histogrammes",
                           disable=not self.verbose):
                histo = np.histogram(img.flatten(), bins=self.bins, range=(0, 1))[0]
                histos.append(histo)
            
            return np.array(histos)
    
    def _plot_histogram_features(self, imgs, histos, n=4):
        """Visualise les histogrammes extraits avec Plotly."""
        n = min(n, len(imgs), len(histos))
        
        if self.use_streamlit and HAS_STREAMLIT:
            st.markdown("### 📊 Extraction d'Histogrammes")
            
            fig = make_subplots(
                rows=2, cols=n,
                row_heights=[0.5, 0.5],
                subplot_titles=[f"Image {i+1}" if i < n else f"Histogramme ({self.bins} bins)" 
                               for i in range(2*n)],
                specs=[[{'type': 'image'}]*n,
                       [{'type': 'bar'}]*n],
                vertical_spacing=0.12,
                horizontal_spacing=0.05
            )
            
            for i in range(n):
                img = imgs[i]
                histo = histos[i]
                
                # Image
                if len(img.shape) == 2:
                    img_rgb = np.stack([img]*3, axis=-1)
                else:
                    img_rgb = img
                fig.add_trace(go.Image(z=img_rgb), row=1, col=i+1)
                
                # Histogramme
                fig.add_trace(
                    go.Bar(x=list(range(self.bins)), y=histo, 
                          marker_color='steelblue', showlegend=False),
                    row=2, col=i+1
                )
            
            fig.update_xaxes(showticklabels=False, row=1)
            fig.update_yaxes(showticklabels=False, row=1)
            fig.update_layout(height=500, title_text=f"Features Histogrammes ({self.bins} bins)")
            
<<<<<<< HEAD
            st.plotly_chart(fig, use_container_width=True)
=======
            st.plotly_chart(fig, width="stretch")
>>>>>>> origin/Dev
            st.info(f"📦 Compression: {imgs[0].size} pixels → {self.bins} features par image")
    
    def visualize(self, X_before: Any, X_after: Any, n_samples: int = 3) -> None:
        """Visualise les histogrammes extraits."""
        import matplotlib.pyplot as plt
        
        # Extraire les images originales
        if isinstance(X_before, pd.DataFrame):
            images = [X_before['image_array'].iloc[i] for i in range(min(n_samples, len(X_before)))]
        else:
            images = X_before[:n_samples]
        
        # X_after contient les histogrammes (n_samples, bins)
        histograms = X_after[:n_samples]
        
        fig, axes = plt.subplots(2, n_samples, figsize=(4*n_samples, 8))
        fig.suptitle(f'ImageHistogram: Extraction de features ({self.bins} bins)', fontsize=16, fontweight='bold')
        
        for i in range(n_samples):
            # Image originale
            axes[0, i].imshow(images[i], cmap='gray' if len(images[i].shape)==2 else None)
            axes[0, i].set_title(f'Image {i+1}')
            axes[0, i].axis('off')
            
            # Histogramme extrait
            axes[1, i].bar(range(self.bins), histograms[i], color='steelblue', alpha=0.7)
            axes[1, i].set_xlabel('Bin')
            axes[1, i].set_ylabel('Fréquence')
            axes[1, i].set_title(f'Histogramme ({self.bins} bins)')
            axes[1, i].grid(alpha=0.3)
        
        plt.tight_layout()
        plt.show()
        
        print(f"\n📊 Statistiques histogrammes:")
        print(f"   - Nombre de bins: {self.bins}")
        print(f"   - Shape output: {X_after.shape}")
        print(f"   - Compression: {images[0].size} pixels → {self.bins} features")
