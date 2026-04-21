"""Stage DVC 2/3 — Entraînement CNN + tracking MLflow.

Lit  : data/processed/{X,y}_train.npy
Écrit: data/models/covid_model.keras  +  outputs/metrics.json
"""
import json
import os
import sys
from pathlib import Path

import mlflow
import mlflow.keras
import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "src"))

from ds_covid.models import build_baseline_cnn  # noqa: E402

PARAMS_FILE  = PROJECT_ROOT / "params.yaml"
PROCESSED    = PROJECT_ROOT / "data" / "processed"
MODELS_DIR   = PROJECT_ROOT / "data" / "models"
METRICS_FILE = PROJECT_ROOT / "outputs" / "metrics.json"


def load_params() -> dict:
    with open(PARAMS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    p       = load_params()
    tp      = p["train"]
    mlp     = p["mlflow"]
    prep    = p["preprocess"]
    img_h, img_w = prep["img_size"]

    print("[INFO] Chargement données prétraitées…", flush=True)
    X_train = np.load(PROCESSED / "X_train.npy")
    y_train = np.load(PROCESSED / "y_train.npy")
    X_test  = np.load(PROCESSED / "X_test.npy")
    y_test  = np.load(PROCESSED / "y_test.npy")
    print(f"[INFO] Train={len(X_train)}  Test={len(X_test)}", flush=True)

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", mlp["tracking_uri"])
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(mlp["experiment_name"])

    with mlflow.start_run():
        mlflow.log_params({
            "epochs":        tp["epochs"],
            "batch_size":    tp["batch_size"],
            "learning_rate": tp["learning_rate"],
            "img_size":      prep["img_size"],
        })

        model = build_baseline_cnn(
            input_shape=(img_h, img_w, 1), num_classes=4
        )

        history = model.fit(
            X_train, y_train,
            epochs=tp["epochs"],
            batch_size=tp["batch_size"],
            validation_data=(X_test, y_test),
            verbose=1,
        )

        val_acc  = float(history.history["val_accuracy"][-1])
        val_loss = float(history.history["val_loss"][-1])
        mlflow.log_metrics({"val_accuracy": val_acc, "val_loss": val_loss})

        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        model_path = MODELS_DIR / "covid_model.keras"
        model.save(model_path)
        mlflow.keras.log_model(model, artifact_path="model",
                               registered_model_name=mlp["model_name"])

        metrics = {
            "val_accuracy": val_acc,
            "val_loss":     val_loss,
            "epochs":       tp["epochs"],
        }
        METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(METRICS_FILE, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        print(f"[INFO] val_accuracy={val_acc:.4f}  val_loss={val_loss:.4f}", flush=True)
        print(f"[INFO] Modèle → {model_path}", flush=True)


if __name__ == "__main__":
    main()
