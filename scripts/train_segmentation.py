"""Stage DVC — Entraînement du U-Net de segmentation pulmonaire + tracking MLflow.

Lit  : data/processed/segmentation/{X,M}_train.npy (re-split en train/val en interne)
Écrit: data/models/lung_unet.keras  +  outputs/segmentation_metrics.json

Entraînement en 2 phases (cf. build_unet) : l'encoder MobileNetV2 pré-entraîné ne doit
pas être fine-tuné en entier dès le départ avec un LR élevé, sous peine de détruire les
poids ImageNet (le val_dice s'effondre en 1-2 epochs si on dégèle tout dès le début).
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
from tqdm.keras import TqdmCallback

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from ds_covid.data import MemmapSequence  # noqa: E402
from ds_covid.segmentation import build_unet, combined_loss, dice_coef, iou_metric  # noqa: E402

PARAMS_FILE  = PROJECT_ROOT / "params.yaml"
PROCESSED    = PROJECT_ROOT / "data" / "processed" / "segmentation"
MODELS_DIR   = PROJECT_ROOT / "data" / "models"
METRICS_FILE = PROJECT_ROOT / "outputs" / "segmentation_metrics.json"


def load_params() -> dict:
    with open(PARAMS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    p    = load_params()
    sp   = p["segmentation"]
    mlp  = p["mlflow"]
    prep = p["preprocess"]
    img_h, img_w = prep["img_size"]

    print("[INFO] Chargement données prétraitées…", flush=True)
    X_train = np.load(PROCESSED / "X_train.npy", mmap_mode="r")
    M_train = np.load(PROCESSED / "M_train.npy", mmap_mode="r")
    print(f"[INFO] Train (avant split val) = {len(X_train)}", flush=True)

    idx_train, idx_val = train_test_split(
        np.arange(len(X_train)),
        test_size=sp["val_split"],
        random_state=prep["random_seed"],
    )
    print(f"[INFO] Train={len(idx_train)}  Val={len(idx_val)}", flush=True)

    train_seq = MemmapSequence(X_train, M_train, batch_size=sp["batch_size"], shuffle=True, indices=idx_train)
    val_seq   = MemmapSequence(X_train, M_train, batch_size=sp["batch_size"], shuffle=False, indices=idx_val)

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", mlp["tracking_uri"])
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(mlp["segmentation_experiment_name"])

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / "lung_unet.keras"

    with mlflow.start_run():
        mlflow.log_params({
            "freeze_epochs":       sp["freeze_epochs"],
            "freeze_lr":           sp["freeze_lr"],
            "fine_tune_epochs":    sp["fine_tune_epochs"],
            "fine_tune_lr":        sp["fine_tune_lr"],
            "batch_size":          sp["batch_size"],
            "fine_tune_batch_size": sp["fine_tune_batch_size"],
            "val_split":           sp["val_split"],
            "img_size":            prep["img_size"],
        })

        model, encoder = build_unet(input_shape=(img_h, img_w, 1))

        # --- Phase 1 : encoder gelé, seul le decoder (initialisé aléatoirement) apprend ---
        for layer in encoder.layers:
            layer.trainable = False

        model.compile(
            optimizer=tf.keras.optimizers.Adam(sp["freeze_lr"]),
            loss=combined_loss, metrics=[dice_coef, iou_metric],
        )
        print(f"--- Phase 1/2 : decoder seul (encoder gelé), jusqu'à {sp['freeze_epochs']} epochs ---", flush=True)

        history_freeze = model.fit(
            train_seq,
            validation_data=val_seq,
            epochs=sp["freeze_epochs"],
            callbacks=[
                tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=3, restore_best_weights=True),
                tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=1, min_lr=1e-5),
                tf.keras.callbacks.ModelCheckpoint(model_path, monitor="val_loss", save_best_only=True),
                TqdmCallback(desc="Phase 1/2 (decoder)", verbose=2),
            ],
            verbose=0,
        )

        # --- Phase 2 : encoder dégelé, fine-tuning complet avec un LR beaucoup plus bas ---
        for layer in encoder.layers:
            layer.trainable = True

        model.compile(
            optimizer=tf.keras.optimizers.Adam(sp["fine_tune_lr"]),
            loss=combined_loss, metrics=[dice_coef, iou_metric],
        )
        print(f"--- Phase 2/2 : fine-tuning complet, jusqu'à {sp['fine_tune_epochs']} epochs ---", flush=True)

        # Fine-tuner tout l'encoder demande de stocker les gradients/activations de tout le
        # réseau : ça peut faire déborder la mémoire GPU au même batch size qu'en phase 1.
        train_seq_ft = MemmapSequence(X_train, M_train, batch_size=sp["fine_tune_batch_size"], shuffle=True, indices=idx_train)
        val_seq_ft   = MemmapSequence(X_train, M_train, batch_size=sp["fine_tune_batch_size"], shuffle=False, indices=idx_val)

        history_finetune = model.fit(
            train_seq_ft,
            validation_data=val_seq_ft,
            epochs=sp["fine_tune_epochs"],
            callbacks=[
                tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=4, restore_best_weights=True),
                tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2, min_lr=1e-7),
                tf.keras.callbacks.ModelCheckpoint(model_path, monitor="val_loss", save_best_only=True),
                TqdmCallback(desc="Phase 2/2 (fine-tune)", verbose=2),
            ],
            verbose=0,
        )

        val_dice = float(history_finetune.history["val_dice_coef"][-1])
        val_iou  = float(history_finetune.history["val_iou_metric"][-1])
        val_loss = float(history_finetune.history["val_loss"][-1])
        mlflow.log_metrics({"val_dice": val_dice, "val_iou": val_iou, "val_loss": val_loss})

        # ModelCheckpoint a déjà sauvegardé le meilleur modèle des 2 phases sur model_path ;
        # on recharge ces poids avant de logger dans le registry, au cas où la dernière
        # epoch de la phase 2 ne serait pas la meilleure (restore_best_weights ne couvre
        # que la phase où il est actif).
        model.load_weights(model_path)
        mlflow.keras.log_model(model, artifact_path="model", registered_model_name=mlp["segmentation_model_name"])

        metrics = {
            "val_dice":  val_dice,
            "val_iou":   val_iou,
            "val_loss":  val_loss,
            "freeze_epochs_run":    len(history_freeze.epoch),
            "fine_tune_epochs_run": len(history_finetune.epoch),
        }
        METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(METRICS_FILE, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        print(f"[INFO] val_dice={val_dice:.4f}  val_iou={val_iou:.4f}  val_loss={val_loss:.4f}", flush=True)
        print(f"[INFO] Modèle → {model_path}", flush=True)


if __name__ == "__main__":
    main()
