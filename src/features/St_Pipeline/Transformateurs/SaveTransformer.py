"""
SaveTransformer - Sauvegarde des features.

Transformateur passthrough pour sauvegarder les données sur disque.
"""

import os
from typing import Any
import numpy as np
import pandas as pd

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

from .base import BaseTransform


class SaveTransformer(BaseTransform):
    """
    Transformateur pour sauvegarder les features extraites.
    
    Ce transformateur sauvegarde les données dans un fichier .npy
    et retourne les données inchangées pour permettre la continuation
    du pipeline.
    
    Pattern sklearn: Transformation passthrough (retourne X sans modification).
    
    Usage:
        saver = SaveTransformer(save_dir="outputs", prefix="features")
        X = saver.fit_transform(X)  # Sauvegarde et retourne X
    """
    
    def __init__(self, save_dir="outputs", prefix="features", **kwargs):
        """
        Initialise le sauvegardeur.
        
        Args:
            save_dir: Répertoire de sauvegarde
            prefix: Préfixe pour le nom de fichier
            **kwargs: Paramètres de BaseTransform (verbose, use_streamlit)
        """
        super().__init__(**kwargs)
        self.save_dir = save_dir
        self.prefix = prefix
        os.makedirs(self.save_dir, exist_ok=True)
    
    def _process(self, X: Any) -> Any:
        """
        Sauvegarde les données et les retourne inchangées.
        
        Args:
            X: Données à sauvegarder
        
        Returns:
            X inchangé (passthrough)
        """
        # Construire le chemin
        path = os.path.join(self.save_dir, f"{self.prefix}.npy")
        
        # Convertir en numpy array si nécessaire
        if isinstance(X, pd.DataFrame):
            # Pour DataFrame, sauvegarder comme pickle
            path = path.replace('.npy', '.pkl')
            X.to_pickle(path)
            self._log(f"DataFrame sauvegardé dans {path}")
            if self.use_streamlit and HAS_STREAMLIT:
                st.success(f"✅ DataFrame sauvegardé : `{path}`")
        else:
            # Pour numpy array
            data_to_save = np.array(X)
            np.save(path, data_to_save)
            self._log(f"Features sauvegardées dans {path} - Shape: {data_to_save.shape}")
            if self.use_streamlit and HAS_STREAMLIT:
                st.success(f"✅ Features sauvegardées : `{path}` - Shape: {data_to_save.shape}")
        
        # Retourner X inchangé (passthrough)
        return X
