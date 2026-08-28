"""Stage DVC 3/4 — Entraînement CNN + tracking MLflow.

Lit  : data/processed/{X,y}_train.npy (re-split en train/val en interne)
Écrit: data/models/classification.keras  +  outputs/metrics.json
"""
import json
import os
import sys
from pathlib import Path

import mlflow
import mlflow.keras
import numpy as np
import tensorflow as tf
import yaml
from dotenv import load_dotenv
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from tqdm.keras import TqdmCallback

TRAINER_ROOT = Path(__file__).parent.parent
REPO_ROOT = TRAINER_ROOT.parent
sys.path.insert(0, str(TRAINER_ROOT / "src"))

# En local (hors Docker), MLFLOW_TRACKING_URI="http://mlflow:5000" (params.yaml)
# ne se résout pas — .env fournit l'override http://localhost:5000. load_dotenv()
# ne touche pas les variables déjà définies dans l'environnement (donc sans effet
# en conteneur, où docker-compose fixe MLFLOW_TRACKING_URI directement).
load_dotenv(REPO_ROOT / ".env")

from ds_covid.data import MemmapSequence  # noqa: E402
from ds_covid.mlflow_utils import DualMlflowRun, MlflowEpochLogger  # noqa: E402
from ds_covid.models import build_cnn  # noqa: E402

PARAMS_FILE  = REPO_ROOT / "params.yaml"
PROCESSED    = REPO_ROOT / "data" / "processed"
MODELS_DIR   = REPO_ROOT / "data" / "models"
METRICS_FILE = REPO_ROOT / "outputs" / "metrics.json"


def flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict:
    items = {}
    for key, value in d.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            items.update(flatten_dict(value, new_key, sep=sep))
        else:
            items[new_key] = value
    return items


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
    # X_test/y_test ne sont pas touchés ici : réservés au stage evaluate, pour un
    # jeu de test jamais vu ni par l'entraînement ni par l'early stopping.
    X_train = np.load(PROCESSED / "X_train.npy", mmap_mode="r")
    y_train = np.load(PROCESSED / "y_train.npy")
    print(f"[INFO] Train (avant split val) = {len(X_train)}", flush=True)

    idx_train, idx_val = train_test_split(
        np.arange(len(y_train)),
        test_size=tp["val_split"],
        stratify=y_train,
        random_state=prep["random_seed"],
    )
    print(f"[INFO] Train={len(idx_train)}  Val={len(idx_val)}", flush=True)

    class_weights = compute_class_weight(
        "balanced", classes=np.unique(y_train[idx_train]), y=y_train[idx_train]
    )
    class_weight_dict = dict(enumerate(class_weights))
    print(f"[INFO] Class weights : {class_weight_dict}", flush=True)

    # class_weight appliqué via sample_weight dans MemmapSequence (pas via l'argument
    # class_weight de model.fit(), incompatible avec un Sequence custom sous Keras 3 —
    # voir ds_covid.data.MemmapSequence). Le split val ne doit pas être pondéré : la
    # pondération ne doit affecter que la loss d'entraînement, pas val_loss (monitorée
    # par EarlyStopping/ReduceLROnPlateau).
    train_seq = MemmapSequence(
        X_train, y_train, batch_size=tp["batch_size"], shuffle=True,
        indices=idx_train, class_weight=class_weight_dict,
    )
    val_seq = MemmapSequence(X_train, y_train, batch_size=tp["batch_size"], shuffle=False, indices=idx_val)

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", mlp["tracking_uri"])
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_registry_uri(tracking_uri)
    mlflow.set_experiment(mlp["experiment_name"])

    remote_tracking_uri = os.getenv("DAGSHUB_MLFLOW_TRACKING_URI")
    remote_registry_uri = remote_tracking_uri if remote_tracking_uri else None

    flat_params = flatten_dict(p)
    flat_params["train.epochs"] = tp["epochs"]
    flat_params["train.batch_size"] = tp["batch_size"]
    flat_params["train.learning_rate"] = tp["learning_rate"]
    flat_params["train.val_split"] = tp["val_split"]
    flat_params["preprocess.img_size"] = prep["img_size"]

    with DualMlflowRun(mlp["experiment_name"]) as tracking:
        tracking.log_params(flat_params)

        model = build_cnn(
            input_shape=(img_h, img_w, 1), num_classes=4, learning_rate=tp["learning_rate"],
        )

        callbacks = [
            tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True),
            tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=3, min_lr=1e-6),
            TqdmCallback(verbose=2),  # 1 barre epoch/epoch (temps écoulé/restant), pas de reset par batch
            MlflowEpochLogger(mirror=tracking),  # métriques loguées dans les deux MLflow
        ]

        history = model.fit(
            train_seq,
            epochs=tp["epochs"],
            validation_data=val_seq,
            callbacks=callbacks,
            verbose=0,
        )

        val_acc  = float(history.history["val_accuracy"][-1])
        val_loss = float(history.history["val_loss"][-1])

        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        model_path = MODELS_DIR / "classification.keras"
        model.save(model_path)

        local_tracking_uri = mlflow.get_tracking_uri()
        local_registry_uri = mlflow.get_registry_uri()

        try:
            mlflow.keras.log_model(model, name="model",
                                   registered_model_name=mlp["model_name"])
        except Exception as error:
            print(f"[WARN] Enregistrement local MLflow ignoré : {error}", flush=True)

        if remote_registry_uri:
            try:
                mlflow.set_tracking_uri(remote_registry_uri)
                mlflow.set_registry_uri(remote_registry_uri)
                mlflow.keras.log_model(model, name="model_remote",
                                       registered_model_name=mlp["model_name"])
                print(f"[INFO] Modèle enregistré dans le registry DagsHub : {mlp['model_name']}", flush=True)
            except Exception as error:
                print(f"[WARN] Enregistrement distant MLflow (DagsHub) ignoré : {error}", flush=True)
            finally:
                mlflow.set_tracking_uri(local_tracking_uri)
                mlflow.set_registry_uri(local_registry_uri)

        tracking.log_model(model, "model")

        metrics = {
            "val_accuracy": val_acc,
            "val_loss":     val_loss,
            "epochs":       len(history.epoch),  # peut être < tp["epochs"] (early stopping)
        }
        METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(METRICS_FILE, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        print(f"[INFO] val_accuracy={val_acc:.4f}  val_loss={val_loss:.4f}", flush=True)
        print(f"[INFO] Modèle → {model_path}", flush=True)


if __name__ == "__main__":
    main()
