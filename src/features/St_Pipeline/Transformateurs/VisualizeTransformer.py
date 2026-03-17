"""
VisualizeTransformer - Visualisation de pipeline.

Transformateur passthrough pour afficher des échantillons d'images.
"""

import os
from typing import Any
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

try:
    import streamlit as st
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

from .base import BaseTransform


class VisualizeTransformer(BaseTransform):
    """
    Transformateur de visualisation pour afficher des échantillons d'images.
    
    Ce transformateur permet de visualiser des images à différentes étapes
    du pipeline pour vérifier les transformations appliquées.
    
    Pattern sklearn: Transformation passthrough (retourne X sans modification).
    
    Usage:
        visualizer = VisualizeTransformer(n_samples=5, prefix="step1")
        X = visualizer.fit_transform(X)  # Affiche 5 images et retourne X
    """
    
    def __init__(self, n_samples=5, prefix="step", save_dir=None, **kwargs):
        """
        Initialise le visualiseur.
        
        Args:
            n_samples: Nombre d'échantillons à afficher
            prefix: Préfixe pour les titres et noms de fichiers
            save_dir: Répertoire pour sauvegarder les images (optionnel)
            **kwargs: Paramètres de BaseTransform (verbose, use_streamlit)
        """
        super().__init__(**kwargs)
        self.n_samples = n_samples
        self.prefix = prefix
        self.save_dir = save_dir
        if self.save_dir:
            os.makedirs(self.save_dir, exist_ok=True)
    
    def _process(self, X: Any) -> Any:
        """
        Visualise des échantillons et retourne X inchangé.
        
        Args:
            X: Données à visualiser
        
        Returns:
            X inchangé (passthrough)
        """
        # Extraire les images selon le format
        if isinstance(X, pd.DataFrame) and 'image_array' in X.columns:
            images = [row['image_array'] for idx, row in X.head(self.n_samples).iterrows()]
        elif isinstance(X, (list, np.ndarray)):
            images = list(X[:self.n_samples])
        else:
            self._log("Format non supporté pour visualisation", level="warning")
            return X
        
        self._log(f"Visualisation de {min(self.n_samples, len(images))} échantillons")
        
        if self.use_streamlit and HAS_STREAMLIT:
            # Mode Streamlit : grille d'images Plotly
            st.subheader(f"🖼️ {self.prefix} - Échantillons")
            
            n = len(images)
            cols = min(3, n)
            rows = (n + cols - 1) // cols
            
            fig = make_subplots(
                rows=rows, cols=cols,
                subplot_titles=[f"Sample {i}" for i in range(n)],
                vertical_spacing=0.05,
                horizontal_spacing=0.02
            )
            
            for i, img in enumerate(images):
                if img is None:
                    continue
                
                row = i // cols + 1
                col = i % cols + 1
                
                img_display = self._prepare_for_display(img)
                fig.add_trace(go.Image(z=img_display), row=row, col=col)
            
            fig.update_xaxes(showticklabels=False)
            fig.update_yaxes(showticklabels=False)
            fig.update_layout(height=300*rows, showlegend=False)
<<<<<<< HEAD
            st.plotly_chart(fig, use_container_width=True)
=======
            st.plotly_chart(fig, width="stretch")
>>>>>>> origin/Dev
        
        else:
            # Mode Matplotlib : affichage classique
            for i, img in enumerate(images):
                if img is None:
                    continue
                
                plt.figure(figsize=(6, 6))
                title = f"{self.prefix} - Sample {i}"
                
                # Ajouter la forme dans le titre
                if hasattr(img, 'shape'):
                    title += f" - shape={img.shape}"
                
                # Affichage selon le type
                if hasattr(img, 'shape'):
                    if len(img.shape) == 2:
                        # Image en niveaux de gris
                        plt.imshow(img, cmap='gray')
                    elif len(img.shape) == 3:
                        # Image couleur
                        plt.imshow(img)
                    else:
                        # Vecteur 1D - afficher comme plot
                        plt.plot(img)
                else:
                    plt.plot(img)
                
                plt.title(title)
                plt.axis('off')
                
                # Sauvegarder si demandé
                if self.save_dir:
                    path = os.path.join(self.save_dir, f"{self.prefix}_sample_{i}.png")
                    plt.savefig(path, bbox_inches='tight')
                    self._log(f"Image sauvegardée : {path}")
                
                plt.show()
                plt.close()
        
        # Retourner X inchangé (passthrough)
        return X
    
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
