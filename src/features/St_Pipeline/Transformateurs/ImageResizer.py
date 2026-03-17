"""
ImageResizer - Redimensionnement d'images.

Transformateur pour redimensionner des images à une taille cible.
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

from .base import BaseTransform


class ImageResizer(BaseTransform):
    """
    Redimensionne les images PIL ou numpy array à la taille souhaitée.
    
    Ce transformateur prend des images (PIL.Image ou numpy arrays) et les redimensionne
    à une taille cible spécifiée.
    
    Pattern sklearn: Transformation stateless (sans apprentissage).
    
    Formats d'entrée supportés:
        - Liste d'images PIL
        - Liste d'images numpy array
        - DataFrame avec colonne 'image_array'
    
    Sortie:
        - Numpy array 4D (batch, height, width, channels) ou 3D (batch, height, width)
        - DataFrame avec colonne 'image_array' mise à jour
    
    Usage:
        resizer = ImageResizer(img_size=(256, 256))
        images_resized = resizer.fit_transform(images_list)
    """
    
    def __init__(self, img_size=(256, 256), **kwargs):
        """
        Initialise le redimensionneur d'images.
        
        Args:
            img_size: Tuple (width, height) pour la taille cible
            **kwargs: Paramètres de BaseTransform (verbose, use_streamlit)
        """
        super().__init__(**kwargs)
        self.img_size = img_size
    
    def _process(self, X: Any) -> Any:
        """
        Redimensionne les images à la taille cible.
        
        Args:
            X: Liste d'images, numpy array ou DataFrame
        
        Returns:
            Images redimensionnées dans le même format que l'entrée
        
        Raises:
            ValueError: Si le format d'entrée n'est pas supporté
        """
        # Cas 1: DataFrame avec colonne 'image_array'
        if isinstance(X, pd.DataFrame):
            if 'image_array' not in X.columns:
                raise ValueError("DataFrame doit contenir une colonne 'image_array'")
            
            self._log(f"Redimensionnement de {len(X)} images en {self.img_size} (DataFrame)")
            
            X_transformed = X.copy()
            resized_images = []
            total = len(X)
            
            # Choisir entre tqdm (console) et Streamlit progress
            if self.use_streamlit and self._progress_bar is not None:
                # Mode Streamlit avec barre de progression
                for idx, (_, row) in enumerate(X.iterrows()):
                    img = row['image_array']
                    if img is not None:
                        resized_images.append(self._resize_image(img))
                    else:
                        resized_images.append(None)
                    
                    # Mise à jour de la progression (tous les 10 items pour performance)
                    if idx % 10 == 0 or idx == total - 1:
                        progress = (idx + 1) / total
                        self._update_progress(progress, f"Redimensionné {idx + 1}/{total} images")
                
                # Nettoyer la barre de progression
                self._clear_progress()
            else:
                # Mode console avec tqdm
                for idx, row in tqdm(X.iterrows(), total=total,
                                    desc=f"[{self.__class__.__name__}] Redimensionnement",
                                    disable=not self.verbose):
                    img = row['image_array']
                    if img is not None:
                        resized_images.append(self._resize_image(img))
                    else:
                        resized_images.append(None)
            
            X_transformed['image_array'] = resized_images
            
            return X_transformed
        
        # Cas 2: Liste d'images
        elif isinstance(X, list):
            self._log(f"Redimensionnement de {len(X)} images en {self.img_size} (liste)")
            
            resized = []
            total = len(X)
            
            if self.use_streamlit and self._progress_bar is not None:
                # Mode Streamlit
                for idx, img in enumerate(X):
                    resized.append(self._resize_image(img))
                    
                    if idx % 10 == 0 or idx == total - 1:
                        progress = (idx + 1) / total
                        self._update_progress(progress, f"Redimensionné {idx + 1}/{total} images")
                
                self._clear_progress()
            else:
                # Mode console avec tqdm
                for img in tqdm(X, desc=f"[{self.__class__.__name__}] Redimensionnement",
                               disable=not self.verbose):
                    resized.append(self._resize_image(img))
            
            return np.array(resized)
        
        # Cas 3: Numpy array (batch d'images)
        elif isinstance(X, np.ndarray):
            self._log(f"Redimensionnement de {X.shape[0]} images en {self.img_size} (numpy array)")
            
            resized = []
            total = X.shape[0]
            
            if self.use_streamlit and self._progress_bar is not None:
                # Mode Streamlit
                for idx, img in enumerate(X):
                    resized.append(self._resize_image(img))
                    
                    if idx % 10 == 0 or idx == total - 1:
                        progress = (idx + 1) / total
                        self._update_progress(progress, f"Redimensionné {idx + 1}/{total} images")
                
                self._clear_progress()
            else:
                # Mode console avec tqdm
                for img in tqdm(X, desc=f"[{self.__class__.__name__}] Redimensionnement",
                               disable=not self.verbose):
                    resized.append(self._resize_image(img))
            
            return np.array(resized)
        
        else:
            raise ValueError(
                f"Format non supporté. Attendu: DataFrame, list ou ndarray, "
                f"reçu: {type(X)}"
            )
    
    def _resize_image(self, image: Any) -> np.ndarray:
        """
        Redimensionne une seule image.
        
        Args:
            image: Image à redimensionner (numpy array ou PIL Image)
        
        Returns:
            Image redimensionnée (numpy array)
        """
        # Conversion en PIL Image si nécessaire
        if isinstance(image, np.ndarray):
            # Gérer les images normalisées [0, 1]
            if image.max() <= 1.0:
                image = (image * 255).astype(np.uint8)
            pil_image = Image.fromarray(image)
        else:
            pil_image = image
        
        # Redimensionnement
        img_resized = pil_image.resize(self.img_size)
        
        return np.array(img_resized)
    
    def visualize(self, X_before: Any, X_after: Any, n_samples: int = 3) -> None:
        """Visualise le redimensionnement avant/après."""
        import matplotlib.pyplot as plt
        
        # Extraire les images depuis DataFrame si nécessaire
        if isinstance(X_before, pd.DataFrame):
            images_before = [X_before['image_array'].iloc[i] for i in range(min(n_samples, len(X_before)))]
            images_after = [X_after['image_array'].iloc[i] for i in range(min(n_samples, len(X_after)))]
        else:
            images_before = X_before[:n_samples]
            images_after = X_after[:n_samples]
        
        fig, axes = plt.subplots(2, n_samples, figsize=(4*n_samples, 8))
        fig.suptitle(f'ImageResizer: Redimensionnement en {self.img_size}', fontsize=16, fontweight='bold')
        
        for i in range(n_samples):
            # Avant
            axes[0, i].imshow(images_before[i], cmap='gray' if len(images_before[i].shape)==2 else None)
            axes[0, i].set_title(f'Avant: {images_before[i].shape}')
            axes[0, i].axis('off')
            
            # Après
            axes[1, i].imshow(images_after[i], cmap='gray' if len(images_after[i].shape)==2 else None)
            axes[1, i].set_title(f'Après: {images_after[i].shape}')
            axes[1, i].axis('off')
        
        plt.tight_layout()
        plt.show()
