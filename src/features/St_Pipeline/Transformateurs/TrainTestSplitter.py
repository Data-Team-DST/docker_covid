"""
TrainTestSplitter - Séparation des données en ensembles train/test/validation.

Transformateur pour créer des splits stratifiés des données.
"""

from typing import Any, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from .base import BaseTransform


class TrainTestSplitter(BaseTransform):
    """
    Transformateur pour séparer les données en ensembles train/test/validation.
    
    Ce transformateur utilise train_test_split de sklearn pour créer des
    splits stratifiés (par défaut) des données. Il peut créer:
    - Train/Test (2 ensembles)
    - Train/Validation/Test (3 ensembles)
    
    Pattern sklearn: Transformation stateless mais retourne un dictionnaire
    contenant les différents splits.
    
    Usage:
        # Split train/test
        splitter = TrainTestSplitter(test_size=0.2, random_state=42)
        splits = splitter.fit_transform(df)
        X_train, y_train = splits['train']
        X_test, y_test = splits['test']
        
        # Split train/val/test
        splitter = TrainTestSplitter(test_size=0.2, val_size=0.2, random_state=42)
        splits = splitter.fit_transform(df)
        X_train, y_train = splits['train']
        X_val, y_val = splits['val']
        X_test, y_test = splits['test']
    """
    
    def __init__(self, 
                 test_size=0.2,
                 val_size=None,
                 random_state=42,
                 stratify=True,
                 label_column='label',
                 **kwargs):
        """
        Initialise le splitter.
        
        Args:
            test_size: Proportion du test set (0.0 à 1.0)
            val_size: Proportion du validation set (optionnel, None = pas de val set)
            random_state: Seed pour reproductibilité
            stratify: Si True, fait un split stratifié (même distribution des labels)
            label_column: Nom de la colonne contenant les labels
            **kwargs: Paramètres de BaseTransform (verbose, use_streamlit)
        """
        super().__init__(**kwargs)
        self.test_size = test_size
        self.val_size = val_size
        self.random_state = random_state
        self.stratify = stratify
        self.label_column = label_column
        
        # Validation des paramètres
        if val_size is not None:
            if test_size + val_size >= 1.0:
                raise ValueError(f"test_size ({test_size}) + val_size ({val_size}) doit être < 1.0")
    
    def _process(self, X: Any) -> dict:
        """
        Sépare les données en ensembles train/test(/val).
        
        Args:
            X: DataFrame contenant les données et labels
        
        Returns:
            Dictionnaire avec les splits:
            - Si val_size=None: {'train': (X_train, y_train), 'test': (X_test, y_test)}
            - Sinon: {'train': (X_train, y_train), 'val': (X_val, y_val), 'test': (X_test, y_test)}
        """
        if not isinstance(X, pd.DataFrame):
            raise ValueError("TrainTestSplitter nécessite un DataFrame en entrée")
        
        if self.label_column not in X.columns:
            raise ValueError(f"Colonne '{self.label_column}' introuvable dans le DataFrame")
        
        # Stratification basée sur les labels
        y = X[self.label_column]
        stratify_array = y if self.stratify else None
        
        if self.val_size is None:
            # Split simple: train/test
            self._log(f"Split train/test: {1-self.test_size:.0%}/{self.test_size:.0%}")
            
            X_train, X_test, y_train, y_test = train_test_split(
                X, y,
                test_size=self.test_size,
                random_state=self.random_state,
                stratify=stratify_array
            )
            
            self._log(f"✅ Train: {len(X_train)} | Test: {len(X_test)}")
            
            # Afficher la distribution des labels
            if self.verbose:
                self._display_label_distribution(y_train, y_test)
            
            return {
                'train': (X_train, y_train),
                'test': (X_test, y_test)
            }
        
        else:
            # Split en 3: train/val/test
            # D'abord: train+val / test
            test_size_initial = self.test_size
            X_trainval, X_test, y_trainval, y_test = train_test_split(
                X, y,
                test_size=test_size_initial,
                random_state=self.random_state,
                stratify=stratify_array
            )
            
            # Ensuite: train / val (sur le train+val)
            # val_size_adjusted = val_size / (1 - test_size)
            val_size_adjusted = self.val_size / (1 - self.test_size)
            stratify_trainval = y_trainval if self.stratify else None
            
            X_train, X_val, y_train, y_val = train_test_split(
                X_trainval, y_trainval,
                test_size=val_size_adjusted,
                random_state=self.random_state,
                stratify=stratify_trainval
            )
            
            train_pct = len(X_train) / len(X)
            val_pct = len(X_val) / len(X)
            test_pct = len(X_test) / len(X)
            
            self._log(f"Split train/val/test: {train_pct:.0%}/{val_pct:.0%}/{test_pct:.0%}")
            self._log(f"✅ Train: {len(X_train)} | Val: {len(X_val)} | Test: {len(X_test)}")
            
            # Afficher la distribution des labels
            if self.verbose:
                self._display_label_distribution(y_train, y_val, y_test)
            
            return {
                'train': (X_train, y_train),
                'val': (X_val, y_val),
                'test': (X_test, y_test)
            }
    
    def _display_label_distribution(self, *label_arrays):
        """Affiche la distribution des labels pour chaque split."""
        import matplotlib.pyplot as plt
        
        split_names = ['Train', 'Val', 'Test'] if len(label_arrays) == 3 else ['Train', 'Test']
        
        print("\n📊 Distribution des labels:")
        for name, labels in zip(split_names, label_arrays):
            counts = labels.value_counts().sort_index()
            print(f"\n{name}:")
            for label, count in counts.items():
                pct = count / len(labels) * 100
                print(f"  - {label}: {count} ({pct:.1f}%)")
        
        # Visualisation
        fig, axes = plt.subplots(1, len(label_arrays), figsize=(6*len(label_arrays), 4))
        if len(label_arrays) == 2:
            axes = [axes[0], axes[1]]
        
        for idx, (name, labels) in enumerate(zip(split_names, label_arrays)):
            counts = labels.value_counts().sort_index()
            axes[idx].bar(range(len(counts)), counts.values, color='steelblue', alpha=0.7)
            axes[idx].set_xticks(range(len(counts)))
            axes[idx].set_xticklabels(counts.index, rotation=45, ha='right')
            axes[idx].set_xlabel('Label')
            axes[idx].set_ylabel('Count')
            axes[idx].set_title(f'{name} Set (n={len(labels)})')
            axes[idx].grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def visualize(self, X_before: Any, X_after: Any, n_samples: int = 3) -> None:
        """Visualise les statistiques des splits."""
        if not isinstance(X_after, dict):
            print("❌ La sortie doit être un dictionnaire de splits")
            return
        
        print("\n📊 Résumé des splits:")
        print("=" * 60)
        
        total_samples = sum(len(split[0]) for split in X_after.values())
        
        for split_name, (X_split, y_split) in X_after.items():
            pct = len(X_split) / total_samples * 100
            print(f"\n{split_name.upper()}:")
            print(f"  - Samples: {len(X_split)} ({pct:.1f}%)")
            print(f"  - Features shape: {X_split.shape}")
            print(f"  - Labels shape: {y_split.shape}")
            print(f"  - Labels uniques: {y_split.nunique()}")
