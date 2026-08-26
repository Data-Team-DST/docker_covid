"""Utilitaires de chargement de données partagés entre les pipelines d'entraînement
(classification et segmentation)."""

from typing import Optional

import numpy as np
import tensorflow as tf


class MemmapSequence(tf.keras.utils.Sequence):
    """Sert les données par batch depuis un .npy memmap, sans jamais charger
    l'ensemble du dataset en RAM (indispensable : après augmentation, les données
    dépassent largement la RAM disponible sur les petites machines).

    `indices` permet de servir un sous-ensemble (ex: split train/val fait à partir
    d'un seul tableau) sans dupliquer les données sur disque. Générique sur la forme
    de `y` : fonctionne aussi bien pour des labels scalaires (classification) que
    pour des masks (H, W, 1) (segmentation)."""

    def __init__(
        self,
        X: np.ndarray,
        y: np.ndarray,
        batch_size: int,
        shuffle: bool,
        indices: Optional[np.ndarray] = None,
        class_weight: Optional[dict] = None,
    ):
        self.X = X
        self.y = y
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.indices = np.arange(len(X)) if indices is None else np.asarray(indices)
        self.class_weight = class_weight
        self.on_epoch_end()

    def __len__(self) -> int:
        return int(np.ceil(len(self.indices) / self.batch_size))

    def __getitem__(self, idx: int):
        batch_idx = np.sort(self.indices[idx * self.batch_size : (idx + 1) * self.batch_size])
        X_batch, y_batch = self.X[batch_idx], self.y[batch_idx]
        if self.class_weight is None:
            return X_batch, y_batch
        # Keras 3 casse (ValueError structure length 2 vs 3) si on passe class_weight=
        # à model.fit() avec un Sequence/générateur custom au lieu d'un tf.data.Dataset —
        # on calcule donc le sample_weight ici plutôt que via l'argument class_weight.
        sample_weight = np.array(
            [self.class_weight[int(label)] for label in y_batch], dtype="float32"
        )
        return X_batch, y_batch, sample_weight

    def on_epoch_end(self) -> None:
        if self.shuffle:
            np.random.shuffle(self.indices)
