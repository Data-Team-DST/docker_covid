"""Stage DVC — Évaluation du U-Net de segmentation sur le jeu de test.

Lit  : data/models/segmentation.keras + data/processed/segmentation/{X,M}_test.npy
Écrit: outputs/segmentation_evaluation_report.json

Métriques calculées sur le mask brut (seuillage à 0.5) ET sur le mask nettoyé
(cf. deep_learning.segmentation.clean_mask), pour vérifier l'apport du post-traitement.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf
import yaml

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "trainer"))

from deep_learning.segmentation import clean_mask, dice_coef, iou_metric  # noqa: E402

PARAMS_FILE = PROJECT_ROOT / "params.yaml"
MODELS_DIR  = PROJECT_ROOT / "data" / "models"
PROCESSED   = PROJECT_ROOT / "data" / "processed" / "segmentation"
EVAL_FILE   = PROJECT_ROOT / "outputs" / "segmentation_evaluation_report.json"


def load_params() -> dict:
    with open(PARAMS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)["segmentation"]


def main() -> None:
    sp = load_params()
    model_path = MODELS_DIR / "segmentation.keras"
    print(f"[INFO] Chargement modèle : {model_path}", flush=True)
    model = tf.keras.models.load_model(model_path, compile=False)

    X_test = np.load(PROCESSED / "X_test.npy")
    M_test = np.load(PROCESSED / "M_test.npy")
    print(f"[INFO] Évaluation sur {len(X_test)} images", flush=True)

    preds = model.predict(X_test, batch_size=sp["batch_size"], verbose=0)

    raw_dice = float(dice_coef(M_test, preds))
    raw_iou  = float(iou_metric(M_test, preds))

    cleaned = np.stack([
        clean_mask(
            (preds[i, :, :, 0] > 0.5).astype(np.uint8) * 255,
            n_components=sp["clean_mask_components"],
            closing_kernel_size=sp["clean_mask_closing_kernel"],
        )
        for i in range(len(preds))
    ]).astype("float32")[..., None] / 255.0

    clean_dice = float(dice_coef(M_test, cleaned))
    clean_iou  = float(iou_metric(M_test, cleaned))

    result = {
        "n_test": len(X_test),
        "raw_mask":     {"dice": raw_dice, "iou": raw_iou},
        "cleaned_mask": {"dice": clean_dice, "iou": clean_iou},
    }

    EVAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(EVAL_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"[INFO] Dice brut={raw_dice:.4f}  Dice nettoyé={clean_dice:.4f}", flush=True)
    print(f"[INFO] Rapport → {EVAL_FILE}", flush=True)


if __name__ == "__main__":
    main()
