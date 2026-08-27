"""Chargement du U-Net + prédiction du mask pulmonaire — singleton thread-safe.

`ModelLoader` dupliqué depuis backend/app/models/loader.py plutôt qu'importé :
ce service reste buildable/déployable indépendamment du backend (cf.
logging_config.py pour la même logique appliquée au logging). Même pattern
MLflow Registry + fallback fichier local que le backend.
"""

import logging
import os
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class ModelLoader:
    """Singleton : charge le modèle une fois au démarrage, le garde en mémoire."""

    def __init__(self):
        self._model = None
        self.is_loaded = False
        self.source: str | None = None  # "registry" ou "local", pour observabilité

    def load(self, model_path: str) -> None:
        """Charge le modèle : MLflow Registry en priorité, fallback fichier local."""
        from segmentation_service.config import settings

        if self._load_from_registry(settings):
            return
        self._load_from_local_file(model_path)

    def _load_from_registry(self, settings) -> bool:
        """Tente MLflow Model Registry. Ne laisse jamais remonter d'exception — retourne
        False si indisponible (ou si le modèle nécessite compile=True et des custom
        objects hors-frontière, cf. docstring de module) : le caller retombe alors sur
        le fichier local."""
        if not settings.mlflow_tracking_uri:
            return False
        try:
            os.environ.setdefault(
                "MLFLOW_HTTP_REQUEST_TIMEOUT",
                str(int(settings.mlflow_lookup_timeout_s)),
            )
            import mlflow

            mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
            uri = f"models:/{settings.mlflow_model_name}/{settings.mlflow_model_stage}"
            self._model = mlflow.keras.load_model(uri)
            self.is_loaded = True
            self.source = "registry"
            logger.info("Modèle chargé depuis MLflow Registry : %s", uri)
            return True
        except Exception as e:  # noqa: BLE001 — fallback voulu, quelle que soit la cause
            logger.warning(
                "MLflow Registry indisponible ou pas de modèle '%s' en stage '%s' (%s) "
                "— fallback sur le fichier local",
                settings.mlflow_model_name,
                settings.mlflow_model_stage,
                e,
            )
            return False

    def _load_from_local_file(self, model_path: str) -> None:
        """Charge le modèle depuis un fichier .keras local (fallback, ou si MLflow
        n'est pas configuré)."""
        path = Path(model_path)

        if not path.exists():
            logger.warning("Fichier modèle introuvable : %s", path)
            logger.warning("→ Mets segmentation.keras dans data/models/ et redémarre")
            return

        try:
            import tensorflow as tf

            # compile=False : ce service ne fait que de l'inférence, jamais de
            # ré-entraînement/évaluation — inutile de désérialiser l'optimizer/loss/
            # metrics (combined_loss, dice_coef, iou_metric), qui vivent dans
            # trainer/src/ds_covid/segmentation.py et ne sont pas importés ici
            # (frontières de service). Sans ce flag, le chargement échoue avec
            # "Could not locate function 'combined_loss'".
            self._model = tf.keras.models.load_model(str(path), compile=False)
            self.is_loaded = True
            self.source = "local"
            logger.info(
                "Modèle chargé : %s (%.1f Mo)", path, path.stat().st_size / 1e6
            )
        except Exception as e:  # noqa: BLE001 — log + is_loaded=False voulu, cause quelconque
            logger.error("Échec chargement modèle : %s", e)

    def predict(self, img_array: np.ndarray) -> np.ndarray:
        """Retourne le mask prédit (shape [H, W, 1]) pour le premier élément du batch."""
        if not self.is_loaded:
            raise RuntimeError("Modèle non chargé")
        preds = self._model.predict(img_array, verbose=0)
        return preds[0]


# Instance globale importée par le router
model_loader = ModelLoader()


def clean_mask(mask: np.ndarray, n_components: int = 2, closing_kernel_size: int = 15) -> np.ndarray:
    """Nettoie un mask prédit : ne garde que les `n_components` plus grandes composantes
    connexes (élimine les îlots parasites) puis comble les petits trous par fermeture
    morphologique.

    Args:
        mask: np.ndarray (H, W) - mask binaire ou en niveaux de gris
        n_components: nombre de composantes connexes à conserver (les plus grandes par aire)
        closing_kernel_size: taille du noyau elliptique utilisé pour la fermeture morphologique

    Returns:
        np.ndarray (H, W) uint8 - mask nettoyé, valeurs {0, 255}
    """
    mask_binary = (mask > 0).astype(np.uint8) * 255

    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask_binary, connectivity=8)
    if n_labels <= 1:
        return mask_binary

    areas = stats[1:, cv2.CC_STAT_AREA]
    n_keep = min(n_components, len(areas))
    keep_labels = np.argsort(areas)[::-1][:n_keep] + 1

    cleaned = np.isin(labels, keep_labels).astype(np.uint8) * 255

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (closing_kernel_size, closing_kernel_size))
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)

    return cleaned


def predict_lung_mask(
    image_bytes: bytes,
    img_size: int,
    clean_components: int,
    clean_kernel: int,
) -> bytes:
    """Décode l'image reçue, prédit le mask via le U-Net, le nettoie, le redimensionne
    à la taille d'origine de l'image, puis l'encode en PNG.

    Args:
        image_bytes: contenu brut de l'image reçue (n'importe quelle taille/format
            décodable par OpenCV)
        img_size: résolution carrée attendue en entrée du U-Net
        clean_components / clean_kernel: cf. `clean_mask`

    Returns:
        bytes - PNG du mask binaire {0, 255}, mêmes largeur/hauteur que l'image reçue

    Raises:
        ValueError - si l'image n'est pas décodable
        RuntimeError - si le modèle n'est pas chargé, ou si l'encodage PNG échoue
    """
    buf = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("Image illisible : format non supporté ou fichier corrompu")

    resized = cv2.resize(img, (img_size, img_size), interpolation=cv2.INTER_LINEAR)
    x = (resized.astype("float32") / 255.0).reshape(1, img_size, img_size, 1)

    pred = model_loader.predict(x)[:, :, 0]
    mask = (pred > 0.5).astype(np.uint8) * 255
    mask = clean_mask(mask, n_components=clean_components, closing_kernel_size=clean_kernel)
    mask = cv2.resize(mask, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)

    ok, png = cv2.imencode(".png", mask)
    if not ok:
        raise RuntimeError("Échec de l'encodage PNG du mask")
    return png.tobytes()
