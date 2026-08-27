"""
Deep Learning Models for COVID-19 Radiography Analysis
"""

from typing import Tuple

import tensorflow as tf
from tensorflow.keras import Model, layers


def build_cnn(
    input_shape: Tuple[int, int, int] = (256, 256, 1),
    num_classes: int = 4,
    learning_rate: float = 1e-3,
) -> tf.keras.Model:
    """
    CNN pour la classification COVID-19 : 4 blocs conv (32/64/128/256) + BatchNorm
    + GlobalAveragePooling, validé dans train.ipynb sur le dataset masqué/cropped/CLAHE.

    Pas d'augmentation intégrée au modèle : l'augmentation (flip/rotation/zoom) est
    faite en amont, offline, par le stage DVC `augment` (US-16) — l'appliquer une
    deuxième fois ici doublerait l'augmentation sur des images déjà augmentées.

    Args:
        input_shape: forme des images en entrée (H, W, C)
        num_classes: nombre de classes à prédire

    Returns:
        Modèle Keras compilé
    """
    inputs = tf.keras.Input(shape=input_shape)

    x = inputs
    for filters in [32, 64, 128, 256]:
        x = layers.Conv2D(filters, 3, padding="same", activation="relu")(x)
        x = layers.BatchNormalization()(x)
        x = layers.MaxPooling2D()(x)

    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dropout(0.5)(x)
    outputs = layers.Dense(num_classes, activation="softmax")(x)

    model = Model(inputs, outputs, name="covid_cnn")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model
