"""
ImageNormalizer - Normalisation d'images.

Transformateur pour normaliser les pixels entre 0 et 1.
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


class ImageNormalizer(BaseTransform):
    """
    Normalise les images pixel-wise entre 0 et 1.
    
    Ce transformateur convertit les pixels d'images (typiquement en [0, 255])
    en valeurs flottantes normalisées entre 0 et 1.
    
    Pattern sklearn: Transformation stateless (sans apprentissage).
    
    Formats d'entrée supportés:
        - Liste d'images (numpy arrays)
        - Numpy array 4D (batch d'images)
        - DataFrame avec colonne 'image_array'
    
    Sortie:
        - Images normalisées avec type float32
        - Même format que l'entrée
    
    Usage:
        normalizer = ImageNormalizer()
        images_norm = normalizer.fit_transform(images)
    """
    
    def _process(self, X: Any) -> Any:
        """
        Normalise les images entre 0 et 1.
        
        Args:
            X: Liste d'images, numpy array ou DataFrame
        
        Returns:
            Images normalisées (float32, valeurs entre 0 et 1)
        """
        # Cas 1: DataFrame
        if isinstance(X, pd.DataFrame):
            if 'image_array' not in X.columns:
                raise ValueError("DataFrame doit contenir une colonne 'image_array'")
            
            self._log(f"Normalisation de {len(X)} images (DataFrame)")
            
            X_transformed = X.copy()
            norm_images = []
            total = len(X)
            
            if self.use_streamlit and self._progress_bar is not None:
                # Mode Streamlit
                for idx, (_, row) in enumerate(X.iterrows()):
                    img = row['image_array']
                    if img is not None:
                        norm_images.append(self._normalize_image(img))
                    else:
                        norm_images.append(None)
                    
                    if idx % 100 == 0 or idx == total - 1:
                        progress = (idx + 1) / total
                        self._update_progress(progress, f"Normalisé {idx + 1}/{total}")
                self._clear_progress()
            else:
                # Mode console avec tqdm
                for idx, row in tqdm(X.iterrows(), total=total,
                                    desc=f"[{self.__class__.__name__}] Normalisation",
                                    disable=not self.verbose):
                    img = row['image_array']
                    if img is not None:
                        norm_images.append(self._normalize_image(img))
                    else:
                        norm_images.append(None)
            
            X_transformed['image_array'] = norm_images
            
            # Visualisation en mode Streamlit
            if self.use_streamlit:
                self._plot_normalization_effect(X['image_array'].tolist()[:4], norm_images[:4])
            
            return X_transformed
        
        # Cas 2: Liste ou numpy array
        else:
            data_array = np.array(X)
            self._log(f"Normalisation de {len(data_array)} images")
            
            # Normalisation directe pour l'ensemble
            X_norm = data_array.astype(np.float32)
            
            # Vérifier si déjà normalisé
            if X_norm.max() > 1.0:
                X_norm = X_norm / 255.0
            
            self._log("Normalisation terminée")
            
            return X_norm
    
    def _normalize_image(self, image: np.ndarray) -> np.ndarray:
        """
        Normalise une seule image.
        
        Args:
            image: Image à normaliser (numpy array)
        
        Returns:
            Image normalisée (float32, valeurs entre 0 et 1)
        """
        img_norm = image.astype(np.float32)
        
        # Vérifier si déjà normalisé
        if img_norm.max() > 1.0:
            img_norm = img_norm / 255.0
        
        return img_norm
    
    def _plot_normalization_effect(self, imgs_before, imgs_after, n=4):
        """Visualise l'effet de la normalisation avec Plotly."""
        n = min(n, len(imgs_before), len(imgs_after))
        
        if self.use_streamlit and HAS_STREAMLIT:
            st.markdown("### 📊 Effet de la Normalisation")
            
            # Créer grille avec images et histogrammes
            fig = make_subplots(
                rows=3, cols=n,
                row_heights=[0.35, 0.35, 0.3],
                subplot_titles=[f"Avant: [{imgs_before[i].min():.1f}, {imgs_before[i].max():.1f}]" 
                               if i < n else f"Après: [0.0, 1.0]" 
                               if i < 2*n else "Distribution" for i in range(3*n)],
                specs=[[{'type': 'image'}]*n,
                       [{'type': 'image'}]*n,
                       [{'type': 'scatter'}]*n],
                vertical_spacing=0.08,
                horizontal_spacing=0.05
            )
            
            for i in range(n):
                img_before = imgs_before[i]
                img_after = imgs_after[i]
                
                # Images avant
                if len(img_before.shape) == 2:
                    img_rgb = np.stack([img_before]*3, axis=-1)
                else:
                    img_rgb = img_before
                fig.add_trace(go.Image(z=img_rgb), row=1, col=i+1)
                
                # Images après
                if len(img_after.shape) == 2:
                    img_rgb = np.stack([img_after]*3, axis=-1)
                else:
                    img_rgb = img_after
                fig.add_trace(go.Image(z=img_rgb), row=2, col=i+1)
                
                # Histogrammes comparatifs
                fig.add_trace(
                    go.Histogram(x=img_before.ravel(), nbinsx=50, name="Avant",
                                marker_color='blue', opacity=0.6, showlegend=(i==0)),
                    row=3, col=i+1
                )
                fig.add_trace(
                    go.Histogram(x=img_after.ravel(), nbinsx=50, name="Après",
                                marker_color='orange', opacity=0.6, showlegend=(i==0)),
                    row=3, col=i+1
                )
            
            fig.update_xaxes(showticklabels=False, row=1)
            fig.update_xaxes(showticklabels=False, row=2)
            fig.update_yaxes(showticklabels=False, row=1)
            fig.update_yaxes(showticklabels=False, row=2)
            fig.update_layout(height=700, title_text="Normalisation [0, 1]", barmode='overlay')
            
<<<<<<< HEAD
            st.plotly_chart(fig, use_container_width=True)
=======
            st.plotly_chart(fig, width="stretch")
>>>>>>> origin/Dev
    
    def visualize(self, X_before: Any, X_after: Any, n_samples: int = 3) -> None:
        """Visualise la normalisation (fallback matplotlib)."""
        import matplotlib.pyplot as plt
        
        # Extraire les images
        if isinstance(X_before, pd.DataFrame):
            images_before = [X_before['image_array'].iloc[i] for i in range(min(n_samples, len(X_before)))]
            images_after = [X_after['image_array'].iloc[i] for i in range(min(n_samples, len(X_after)))]
        else:
            images_before = X_before[:n_samples]
            images_after = X_after[:n_samples]
        
        fig, axes = plt.subplots(3, n_samples, figsize=(4*n_samples, 12))
        fig.suptitle('ImageNormalizer: Normalisation 0-1', fontsize=16, fontweight='bold')
        
        for i in range(n_samples):
            # Avant
            axes[0, i].imshow(images_before[i], cmap='gray' if len(images_before[i].shape)==2 else None)
            axes[0, i].set_title(f'Avant: [{images_before[i].min():.3f}, {images_before[i].max():.3f}]')
            axes[0, i].axis('off')
            
            # Après
            axes[1, i].imshow(images_after[i], cmap='gray' if len(images_after[i].shape)==2 else None)
            axes[1, i].set_title(f'Après: [{images_after[i].min():.3f}, {images_after[i].max():.3f}]')
            axes[1, i].axis('off')
            
            # Histogrammes
            axes[2, i].hist(images_before[i].ravel(), bins=50, alpha=0.5, label='Avant', color='blue')
            axes[2, i].hist(images_after[i].ravel(), bins=50, alpha=0.5, label='Après', color='orange')
            axes[2, i].set_xlabel('Intensité')
            axes[2, i].set_ylabel('Fréquence')
            axes[2, i].legend()
            axes[2, i].grid(alpha=0.3)
        
        plt.tight_layout()
        plt.show()
        
        print(f"\n📊 Statistiques normalisation:")
        print(f"   - Avant: [{images_before[0].min():.3f}, {images_before[0].max():.3f}]")
        print(f"   - Après: [{images_after[0].min():.3f}, {images_after[0].max():.3f}]")
    
    def visualize(self, X_before: Any, X_after: Any, n_samples: int = 3) -> None:
        """Visualise la normalisation (fallback matplotlib)."""
        import matplotlib.pyplot as plt
        
        # Extraire les images
        if isinstance(X_before, pd.DataFrame):
            images_before = [X_before['image_array'].iloc[i] for i in range(min(n_samples, len(X_before)))]
            images_after = [X_after['image_array'].iloc[i] for i in range(min(n_samples, len(X_after)))]
        else:
            images_before = X_before[:n_samples]
            images_after = X_after[:n_samples]
        
        fig, axes = plt.subplots(3, n_samples, figsize=(4*n_samples, 12))
        fig.suptitle('ImageNormalizer: Normalisation 0-1', fontsize=16, fontweight='bold')
        
        for i in range(n_samples):
            # Avant
            axes[0, i].imshow(images_before[i], cmap='gray' if len(images_before[i].shape)==2 else None)
            axes[0, i].set_title(f'Avant: [{images_before[i].min():.3f}, {images_before[i].max():.3f}]')
            axes[0, i].axis('off')
            
            # Après
            axes[1, i].imshow(images_after[i], cmap='gray' if len(images_after[i].shape)==2 else None)
            axes[1, i].set_title(f'Après: [{images_after[i].min():.3f}, {images_after[i].max():.3f}]')
            axes[1, i].axis('off')
            
            # Histogrammes
            axes[2, i].hist(images_before[i].ravel(), bins=50, alpha=0.5, label='Avant', color='blue')
            axes[2, i].hist(images_after[i].ravel(), bins=50, alpha=0.5, label='Après', color='orange')
            axes[2, i].set_xlabel('Intensité')
            axes[2, i].set_ylabel('Fréquence')
            axes[2, i].legend()
            axes[2, i].grid(alpha=0.3)
        
        plt.tight_layout()
        plt.show()
