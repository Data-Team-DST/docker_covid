"""Stage DVC 3/3 — Évaluation du modèle entraîné.

Lit  : data/models/covid_model.keras + data/processed/{X,y}_test.npy
Écrit: outputs/evaluation_report.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf
from sklearn.metrics import classification_report, confusion_matrix

PROJECT_ROOT   = Path(__file__).parent.parent
MODELS_DIR     = PROJECT_ROOT / "data" / "models"
PROCESSED      = PROJECT_ROOT / "data" / "processed"
EVAL_FILE      = PROJECT_ROOT / "outputs" / "evaluation_report.json"

CLASS_NAMES = ["COVID", "Normal", "Viral Pneumonia", "Lung_Opacity"]


def main() -> None:
    model_path = MODELS_DIR / "covid_model.keras"
    print(f"[INFO] Chargement modèle : {model_path}", flush=True)
    model = tf.keras.models.load_model(model_path)

    X_test = np.load(PROCESSED / "X_test.npy")
    y_test = np.load(PROCESSED / "y_test.npy")
    print(f"[INFO] Évaluation sur {len(X_test)} images", flush=True)

    y_pred_proba = model.predict(X_test, verbose=0)
    y_pred = np.argmax(y_pred_proba, axis=1)

    accuracy = float(np.mean(y_pred == y_test))
    report   = classification_report(
        y_test, y_pred, target_names=CLASS_NAMES,
        output_dict=True, zero_division=0,
    )
    cm = confusion_matrix(y_test, y_pred).tolist()

    result = {
        "accuracy":    accuracy,
        "report":      report,
        "confusion_matrix": cm,
        "class_names": CLASS_NAMES,
    }

    EVAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(EVAL_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"[INFO] Accuracy : {accuracy:.4f}", flush=True)
    print(f"[INFO] Rapport  → {EVAL_FILE}", flush=True)


if __name__ == "__main__":
    main()
