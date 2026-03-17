"""
DatasetStatistics - Calcule et visualise statistiques du dataset.

Transformateur pour analyser la distribution des classes, dimensions d'images,
et statistiques d'intensité pixel.
"""

from typing import Any, Optional, Dict
import numpy as np
import pandas as pd
from collections import Counter

try:
    import streamlit as st
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

from .base import BaseTransform


class DatasetStatistics(BaseTransform):
    """
    Calcule statistiques complètes et génère visualisations exploratoires.
    
    Ce transformateur analyse le dataset et génère des visualisations
    pour comprendre la distribution des classes, les dimensions des images,
    et les statistiques d'intensité des pixels.
    
    Stats calculées:
    - Distribution des classes (counts, %)
    - Dimensions des images (unique sizes, modes)
    - Intensité pixels par classe (mean, std, min, max, quantiles)
    - Balance des classes (déséquilibre ratio)
    - Présence de masques (% images avec masques)
    
    Pattern sklearn: Pass-through transformer (retourne X inchangé).
    
    Attributs:
        compute_pixel_stats (bool): Calculer stats d'intensité (coûteux)
        n_samples_per_class (int): Nombre d'échantillons pour stats pixel
        stats_ (dict): Statistiques calculées lors du fit()
    
    Usage:
        stats = DatasetStatistics(compute_pixel_stats=True)
        df = stats.fit_transform(df, y=labels)
        print(stats.stats_)
    """
    
    def __init__(self, compute_pixel_stats=False, n_samples_per_class=200, **kwargs):
        """
        Initialise le calculateur de statistiques.
        
        Args:
            compute_pixel_stats: Si True, calcule stats d'intensité (lent)
            n_samples_per_class: Nombre d'échantillons par classe pour stats pixel
            **kwargs: BaseTransform parameters (verbose, use_streamlit)
        """
        super().__init__(**kwargs)
        self.compute_pixel_stats = compute_pixel_stats
        self.n_samples_per_class = n_samples_per_class
        self.stats_ = {}
    
    def _fit(self, X, y=None):
        """
        Calcule toutes les statistiques sur le DataFrame.
        
        Args:
            X: DataFrame avec colonnes ['image_path', 'label', ...]
            y: Labels (optionnel si déjà dans X)
        """
        if not isinstance(X, pd.DataFrame):
            raise ValueError("DatasetStatistics requiert un DataFrame en entrée")
        
        if 'label' not in X.columns:
            raise ValueError("DataFrame doit contenir une colonne 'label'")
        
        self._log("Calcul des statistiques du dataset...")
        
        # Stats générales
        self.stats_['n_total'] = len(X)
        self.stats_['class_distribution'] = X['label'].value_counts().to_dict()
        self.stats_['class_percentages'] = (X['label'].value_counts(normalize=True) * 100).to_dict()
        
        # Balance des classes
        counts = list(self.stats_['class_distribution'].values())
        self.stats_['class_balance_ratio'] = max(counts) / min(counts) if min(counts) > 0 else float('inf')
        
        # Masques
        if 'mask_path' in X.columns:
            self.stats_['has_masks'] = X['mask_path'].notna().sum()
            self.stats_['mask_percentage'] = (self.stats_['has_masks'] / self.stats_['n_total']) * 100
        
        # Stats d'intensité pixel (optionnel)
        if self.compute_pixel_stats and 'image_array' in X.columns:
            self._log(f"Calcul des stats d'intensité (échantillonnage {self.n_samples_per_class} par classe)...")
            pixel_stats = {}
            
            for label in X['label'].unique():
                sample_df = X[X['label'] == label]
                n_samples = min(self.n_samples_per_class, len(sample_df))
                sample = sample_df.sample(n_samples, random_state=42)
                
                # Concatener tous les pixels
                intensities = np.concatenate([
                    img.flatten() for img in sample['image_array'].values if img is not None
                ])
                
                pixel_stats[label] = {
                    'mean': float(np.mean(intensities)),
                    'std': float(np.std(intensities)),
                    'min': float(np.min(intensities)),
                    'max': float(np.max(intensities)),
                    'q25': float(np.percentile(intensities, 25)),
                    'q50': float(np.percentile(intensities, 50)),
                    'q75': float(np.percentile(intensities, 75))
                }
            
            self.stats_['pixel_intensity'] = pixel_stats
        
        self._log(f"Statistiques calculées: {self.stats_['n_total']} images, {len(self.stats_['class_distribution'])} classes")
    
    def _process(self, X):
        """
        Génère visualisations et retourne X inchangé.
        
        Args:
            X: DataFrame
        
        Returns:
            X inchangé (pass-through)
        """
        if not self.stats_:
            self._log("Aucune statistique calculée. fit() requis.", level="warning")
            return X
        
        # Générer visualisations
        self._plot_class_distribution()
        
        if 'pixel_intensity' in self.stats_:
            self._plot_pixel_intensity_analysis()
        
        # Retourner X inchangé
        return X
    
    def _plot_class_distribution(self):
        """Bar chart + pie chart de la distribution des classes."""
        if self.use_streamlit and HAS_STREAMLIT:
            st.subheader("📊 Distribution des Classes")
            
            # Préparer données
            classes = list(self.stats_['class_distribution'].keys())
            counts = list(self.stats_['class_distribution'].values())
            percentages = [self.stats_['class_percentages'][c] for c in classes]
            
            # Plotly bar chart
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(
                    x=classes,
                    y=counts,
                    labels={'x': 'Classe', 'y': 'Nombre d\'images'},
                    title='Distribution des Classes',
                    color=classes,
                    text=counts
                )
                fig.update_traces(texttemplate='%{text}', textposition='outside')
                fig.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig, width="stretch")
            
            with col2:
                # Pie chart
                fig_pie = px.pie(
                    values=counts,
                    names=classes,
                    title='Proportion des Classes (%)',
                    hole=0.3
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, width="stretch")
            
            # Tableau des stats
            st.markdown("**📋 Détails par Classe**")
            df_stats = pd.DataFrame({
                'Classe': classes,
                'Nombre': counts,
                'Pourcentage': [f"{p:.2f}%" for p in percentages]
            })
            st.dataframe(df_stats, width="stretch")
            
            # Métriques clés
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Images", self.stats_['n_total'])
            with col2:
                st.metric("Nombre de Classes", len(classes))
            with col3:
                ratio = self.stats_.get('class_balance_ratio', 0)
                st.metric("Ratio Déséquilibre", f"{ratio:.2f}x")
                if ratio > 3:
                    st.warning("⚠️ Dataset déséquilibré")
        
        else:
            # Matplotlib pour notebooks
            import matplotlib.pyplot as plt
            
            classes = list(self.stats_['class_distribution'].keys())
            counts = list(self.stats_['class_distribution'].values())
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
            
            # Bar chart
            bars = ax1.bar(classes, counts, color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A'])
            ax1.set_title('Distribution des Classes', fontsize=14, fontweight='bold')
            ax1.set_xlabel('Classe')
            ax1.set_ylabel('Nombre d\'images')
            ax1.tick_params(axis='x', rotation=45)
            
            # Ajouter valeurs sur les barres
            for bar in bars:
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}',
                        ha='center', va='bottom')
            
            # Pie chart
            ax2.pie(counts, labels=classes, autopct='%1.1f%%', startangle=90,
                   colors=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A'])
            ax2.set_title('Proportion des Classes', fontsize=14, fontweight='bold')
            
            plt.tight_layout()
            plt.show()
            
            # Print stats
            print("\n📊 Statistiques du Dataset:")
            print(f"  • Total: {self.stats_['n_total']} images")
            print(f"  • Classes: {len(classes)}")
            for classe, count in self.stats_['class_distribution'].items():
                pct = self.stats_['class_percentages'][classe]
                print(f"  • {classe}: {count} ({pct:.2f}%)")
    
    def _plot_pixel_intensity_analysis(self):
        """Box plots et stats d'intensité par classe."""
        if 'pixel_intensity' not in self.stats_:
            return
        
        if self.use_streamlit and HAS_STREAMLIT:
            st.subheader("🎨 Analyse d'Intensité Pixel")
            
            # Préparer données pour box plot
            classes = list(self.stats_['pixel_intensity'].keys())
            data_list = []
            
            for label in classes:
                stats = self.stats_['pixel_intensity'][label]
                data_list.append({
                    'Classe': label,
                    'Mean': stats['mean'],
                    'Std': stats['std'],
                    'Min': stats['min'],
                    'Max': stats['max'],
                    'Q25': stats['q25'],
                    'Q50': stats['q50'],
                    'Q75': stats['q75']
                })
            
            df = pd.DataFrame(data_list)
            
            # Tableau stats
            st.dataframe(df,width="stretch")
            
            # Box plot interactif
            fig = go.Figure()
            
            for label in classes:
                stats = self.stats_['pixel_intensity'][label]
                fig.add_trace(go.Box(
                    name=label,
                    q1=[stats['q25']],
                    median=[stats['q50']],
                    q3=[stats['q75']],
                    lowerfence=[stats['min']],
                    upperfence=[stats['max']],
                    mean=[stats['mean']],
                    boxmean='sd'
                ))
            
            fig.update_layout(
                title='Distribution Intensité Pixel par Classe',
                yaxis_title='Intensité',
                showlegend=True,
                height=400
            )
            st.plotly_chart(fig, width="stretch")
        
        else:
            # Matplotlib
            import matplotlib.pyplot as plt
            
            classes = list(self.stats_['pixel_intensity'].keys())
            
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Préparer données pour box plot
            positions = []
            data_to_plot = []
            
            for i, label in enumerate(classes):
                stats = self.stats_['pixel_intensity'][label]
                positions.append(i)
                # Créer distribution approximative pour box plot
                data_to_plot.append([
                    stats['min'],
                    stats['q25'],
                    stats['q50'],
                    stats['q75'],
                    stats['max']
                ])
            
            bp = ax.boxplot(data_to_plot, positions=positions, labels=classes,
                           patch_artist=True)
            
            # Colorer les boxes
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
            
            ax.set_title('Distribution Intensité Pixel par Classe', fontsize=14, fontweight='bold')
            ax.set_ylabel('Intensité Pixel')
            ax.set_xlabel('Classe')
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.show()
            
            # Print stats
            print("\n🎨 Statistiques d'Intensité Pixel:")
            for label, stats in self.stats_['pixel_intensity'].items():
                print(f"\n  {label}:")
                print(f"    Mean: {stats['mean']:.3f}")
                print(f"    Std:  {stats['std']:.3f}")
                print(f"    Range: [{stats['min']:.3f}, {stats['max']:.3f}]")
