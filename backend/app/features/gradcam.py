"""Grad-CAM — explique une prédiction en surlignant les zones de l'image qui ont pesé
dans le choix de la classe (contrairement au masque de segmentation, qui montre où sont
les poumons, pas pourquoi le modèle a tranché pour telle classe).

Modèle réel = petit CNN maison (4 blocs conv, cf. trainer/src/ds_covid/models.py), pas
un backbone lourd type InceptionV3 — une passe forward+backward supplémentaire reste
rapide, pas d'impact notable sur la latence déjà mesurée.
"""

import cv2
import numpy as np
import tensorflow as tf


def _find_last_conv_layer(model) -> str:
    """Dernière couche à sortie 4D (spatiale) du modèle — évite de coder en dur un nom
    de couche Keras auto-généré, qui peut varier d'un ré-entraînement à l'autre."""
    for layer in reversed(model.layers):
        if len(layer.output.shape) == 4:
            return layer.name
    raise ValueError("Aucune couche convolutionnelle trouvée pour Grad-CAM")


def compute_gradcam_png(model, img_array: np.ndarray) -> bytes:
    """Calcule la heatmap Grad-CAM pour la classe prédite et la renvoie en PNG, overlay
    sur l'image prétraitée (celle réellement vue par le modèle).

    Args:
        model: modèle Keras chargé (cf. ModelLoader.get_model())
        img_array: tenseur prétraité, shape (1, H, W, 1), identique à celui envoyé à
            model.predict() — cf. preprocess_image()

    Returns:
        bytes PNG (heatmap couleur superposée à l'image en niveaux de gris)
    """
    last_conv_layer = _find_last_conv_layer(model)
    grad_model = tf.keras.models.Model(
        model.inputs, [model.get_layer(last_conv_layer).output, model.output]
    )

    with tf.GradientTape() as tape:
        conv_output, predictions = grad_model(img_array)
        predicted_idx = tf.argmax(predictions[0])
        class_score = predictions[:, predicted_idx]

    grads = tape.gradient(class_score, conv_output)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

    conv_output = conv_output[0]
    heatmap = conv_output @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)
    heatmap = tf.maximum(heatmap, 0) / (tf.reduce_max(heatmap) + 1e-8)
    heatmap = heatmap.numpy()

    h, w = img_array.shape[1], img_array.shape[2]
    heatmap = cv2.resize(heatmap, (w, h))
    heatmap_color = cv2.applyColorMap((heatmap * 255).astype("uint8"), cv2.COLORMAP_JET)

    base_gray = ((img_array[0, :, :, 0] + 1.0) * 127.5).astype("uint8")
    base_bgr = cv2.cvtColor(base_gray, cv2.COLOR_GRAY2BGR)
    overlay = cv2.addWeighted(base_bgr, 0.6, heatmap_color, 0.4, 0)

    success, png_bytes = cv2.imencode(".png", overlay)
    if not success:
        raise ValueError("Échec encodage PNG de la heatmap Grad-CAM")
    return png_bytes.tobytes()
