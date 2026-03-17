"""
ImageAnalyser - Analyse d'images et chargement en mémoire.

Transformateur pour analyser les métadonnées des images et optionnellement
les charger en mémoire.
"""

from typing import Any, Optional
import os
import numpy as np
import pandas as pd
from tqdm import tqdm
from PIL import Image
from collections import Counter

try:
    import streamlit as st
    import plotly.express as px
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

from .base import BaseTransform


class ImageAnalyser(BaseTransform):
    """
    Analyse les images et calcule des statistiques détaillées.
    
    Ce transformateur analyse les métadonnées des images (dimensions, 
    tailles de fichiers) lors du fit(), puis peut optionnellement
    charger les images en mémoire lors du transform().
    
    Design: Séparation des responsabilités
    - fit(): Analyse légère (métadonnées uniquement)
    - transform(): Chargement optionnel + enrichissement du DataFrame
    
    Attributs:
        load_images (bool): Charge les images en mémoire lors du transform()
        analyze_masks (bool): Analyse également les masques
        stats_ (dict): Statistiques calculées lors du fit()
    
    Usage:
        # Analyse seule (pas de chargement d'images)
        analyzer = ImageAnalyser(load_images=False)
        analyzer.fit(df)
        print(analyzer.stats_)
        
        # Avec chargement d'images
        analyzer = ImageAnalyser(load_images=True)
        df_enriched = analyzer.fit_transform(df)
    """
    
    def __init__(self, load_images: bool = False, analyze_masks: bool = False, **kwargs):
        """
        Initialise l'analyseur d'images.
        
        Args:
            load_images: Si True, charge les images en mémoire lors du transform()
            analyze_masks: Si True, analyse également les masques
            **kwargs: Paramètres de BaseTransform (verbose, use_streamlit)
        """
        super().__init__(**kwargs)
        self.load_images = load_images
        self.analyze_masks = analyze_masks
        self.stats_ = {}
    
    def _fit(self, X: pd.DataFrame, y: Optional[Any] = None) -> None:
        """
        Analyse les métadonnées des images (dimensions, tailles).
        
        Pattern sklearn: fit = apprentissage/analyse des métadonnées.
        N'analyse que les métadonnées (pas de chargement complet).
        
        Args:
            X: DataFrame avec colonnes ['image_path', 'mask_path', 'label']
            y: Ignoré
        """
        if X is None or len(X) == 0:
            self._log("Aucune donnée à analyser", level="warning")
            return
        
        self._log(f"Analyse de {len(X)} images")
        
        # Statistiques de base
        self.stats_['total_images'] = len(X)
        self.stats_['labels_distribution'] = X['label'].value_counts().to_dict()
        
        # Analyse des dimensions et tailles
        image_dims = []
        mask_dims = []
        file_sizes = []
        
        total = len(X)
        if self.use_streamlit and self._progress_bar is not None:
            # Mode Streamlit
            for idx, (_, row) in enumerate(X.iterrows()):
                try:
                    with Image.open(row['image_path']) as img:
                        image_dims.append(img.size)
                        file_sizes.append(os.path.getsize(row['image_path']))
                    
                    if self.analyze_masks and 'mask_path' in row and pd.notna(row['mask_path']):
                        with Image.open(row['mask_path']) as mask:
                            mask_dims.append(mask.size)
                except Exception as e:
                    if self.verbose:
                        self._log(f"Erreur: {e}", level="warning")
                
                if idx % 100 == 0 or idx == total - 1:
                    progress = (idx + 1) / total
                    self._update_progress(progress, f"Analysé {idx + 1}/{total}")
            self._clear_progress()
        else:
            # Mode console avec tqdm
            for idx, row in tqdm(X.iterrows(), total=total,
                                desc=f"[{self.__class__.__name__}] Analyse métadonnées",
                                disable=not self.verbose):
                try:
                    # Analyse de l'image (métadonnées uniquement)
                    with Image.open(row['image_path']) as img:
                        image_dims.append(img.size)  # (width, height)
                        file_sizes.append(os.path.getsize(row['image_path']))
                    
                    # Analyse du masque
                    if self.analyze_masks and 'mask_path' in row and pd.notna(row['mask_path']):
                        with Image.open(row['mask_path']) as mask:
                            mask_dims.append(mask.size)
                except Exception as e:
                    self._log(f"Erreur: {row['image_path']}: {e}", level="warning")
        
        # Statistiques des dimensions
        self.stats_['image_dimensions'] = Counter(image_dims)
        self.stats_['unique_dimensions'] = len(set(image_dims))
        self.stats_['most_common_size'] = (
            Counter(image_dims).most_common(1)[0][0] if image_dims else None
        )
        
        if mask_dims:
            self.stats_['mask_dimensions'] = Counter(mask_dims)
        
        # Statistiques des tailles de fichiers
        if file_sizes:
            self.stats_['avg_file_size_mb'] = np.mean(file_sizes) / (1024 * 1024)
            self.stats_['min_file_size_mb'] = np.min(file_sizes) / (1024 * 1024)
            self.stats_['max_file_size_mb'] = np.max(file_sizes) / (1024 * 1024)
        
        self._log(f"Analyse terminée: {self.stats_['unique_dimensions']} dimensions uniques")
        
        # Affichage Streamlit
        if self.use_streamlit:
            self._display_statistics()
    
    def _process(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Charge les images (optionnel) et enrichit le DataFrame.
        
        Pattern sklearn: transform = application de la transformation.
        
        Args:
            X: DataFrame avec colonnes ['image_path', 'mask_path', 'label']
        
        Returns:
            DataFrame enrichi avec colonnes optionnelles:
            - image_array: array numpy de l'image (si load_images=True)
            - mask_array: array numpy du masque (si analyze_masks=True)
            - mean_intensity: intensité moyenne (si load_images=True)
            - std_intensity: écart-type (si load_images=True)
            - channels: nombre de canaux (si load_images=True)
        """
        if not self.load_images:
            self._log("Chargement désactivé, retour du DataFrame original")
            return X
        
        self._log(f"Chargement de {len(X)} images en mémoire")
        
        # Copie du DataFrame
        X_transformed = X.copy()
        
        # Listes pour les nouvelles colonnes
        images_array = []
        masks_array = []
        mean_intensities = []
        std_intensities = []
        channels_info = []
        
        total = len(X)
        if self.use_streamlit and self._progress_bar is not None:
            # Mode Streamlit
            for idx, (_, row) in enumerate(X.iterrows()):
                try:
                    img = Image.open(row['image_path'])
                    img_array = np.array(img)
                    images_array.append(img_array)
                    mean_intensities.append(img_array.mean())
                    std_intensities.append(img_array.std())
                    channels_info.append(img_array.shape[-1] if len(img_array.shape) == 3 else 1)
                    
                    if self.analyze_masks and 'mask_path' in row and pd.notna(row['mask_path']):
                        mask = Image.open(row['mask_path'])
                        masks_array.append(np.array(mask))
                    else:
                        masks_array.append(None)
                except Exception as e:
                    images_array.append(None)
                    masks_array.append(None)
                    mean_intensities.append(None)
                    std_intensities.append(None)
                    channels_info.append(None)
                
                if idx % 50 == 0 or idx == total - 1:
                    progress = (idx + 1) / total
                    self._update_progress(progress, f"Chargé {idx + 1}/{total}")
            self._clear_progress()
        else:
            # Mode console avec tqdm
            for idx, row in tqdm(X.iterrows(), total=total,
                                desc=f"[{self.__class__.__name__}] Chargement images",
                                disable=not self.verbose):
                try:
                    # Charger l'image
                    img = Image.open(row['image_path'])
                    img_array = np.array(img)
                    images_array.append(img_array)
                    
                    # Statistiques de l'image
                    mean_intensities.append(img_array.mean())
                    std_intensities.append(img_array.std())
                    channels_info.append(
                        img_array.shape[-1] if len(img_array.shape) == 3 else 1
                    )
                    
                    # Charger le masque si demandé
                    if (self.analyze_masks and 'mask_path' in row 
                        and pd.notna(row['mask_path'])):
                        mask = Image.open(row['mask_path'])
                        masks_array.append(np.array(mask))
                    else:
                        masks_array.append(None)
                except Exception as e:
                    self._log(f"Erreur: {row['image_path']}: {e}", level="warning")
                    images_array.append(None)
                    masks_array.append(None)
                    mean_intensities.append(np.nan)
                    std_intensities.append(np.nan)
                    channels_info.append(np.nan)
        
        # Enrichir le DataFrame
        X_transformed['image_array'] = images_array
        if self.analyze_masks:
            X_transformed['mask_array'] = masks_array
        X_transformed['mean_intensity'] = mean_intensities
        X_transformed['std_intensity'] = std_intensities
        X_transformed['channels'] = channels_info
        
        self._log(f"Chargement terminé: {len(X_transformed)} images chargées")
        
        # Affichage Streamlit
        if self.use_streamlit:
            self._analyze_by_label(X_transformed)
        
        return X_transformed
    
    def _display_statistics(self) -> None:
        """Affiche les statistiques collectées lors du fit()."""
        if not HAS_STREAMLIT or not self.use_streamlit:
            # Affichage console
            print("\n" + "="*60)
            print("STATISTIQUES DES IMAGES")
            print("="*60)
            for key, value in self.stats_.items():
                if key not in ['image_dimensions', 'mask_dimensions']:
                    print(f"{key}: {value}")
            return
            
        st.subheader("📊 Statistiques des Images")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Images", self.stats_['total_images'])
        with col2:
            st.metric("Dimensions Uniques", self.stats_['unique_dimensions'])
        with col3:
            st.metric("Taille Moyenne", 
                     f"{self.stats_.get('avg_file_size_mb', 0):.2f} MB")
        with col4:
            size = self.stats_.get('most_common_size')
            st.metric("Taille Commune", 
                     f"{size[0]}x{size[1]}" if size else "N/A")
    
    def _analyze_by_label(self, X_transformed: pd.DataFrame) -> None:
        """Analyse et affiche les statistiques par label (Streamlit)."""
        if not HAS_STREAMLIT or not self.use_streamlit:
            return
            
        st.subheader("🔍 Analyse par Label")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Statistiques d'intensité par label
            intensity_stats = X_transformed.groupby('label').agg({
                'mean_intensity': ['mean', 'std'],
                'std_intensity': ['mean', 'std']
            }).round(2)
            st.write("**Statistiques d'Intensité**")
            st.dataframe(intensity_stats, width="stretch")
        
        with col2:
            # Box plot des intensités
            fig = px.box(
                X_transformed, x='label', y='mean_intensity',
                title="Distribution de l'Intensité par Label",
                color='label'
            )
            st.plotly_chart(fig, width="stretch")
