"""Stage DVC 1/3 — Prétraitement des images.

Lit  : data/raw/COVID-19_Radiography_Dataset/{classe}/images/
Écrit: data/processed/{X,y}_{train,test}.npy
"""
import json
import sys
from pathlib import Path

import numpy as np
import yaml
from PIL import Image
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "src"))

PARAMS_FILE = PROJECT_ROOT / "params.yaml"
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "COVID-19_Radiography_Dataset"
OUT_DIR = PROJECT_ROOT / "data" / "processed"
STATS_FILE = PROJECT_ROOT / "outputs" / "preprocess_stats.json"


def load_params() -> dict:
    with open(PARAMS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)["preprocess"]


def load_images(params: dict) -> tuple[np.ndarray, np.ndarray]:
    img_h, img_w = params["img_size"]
    max_n = params["max_samples_per_class"]
    classes: dict = params["classes"]

    X, y = [], []
    counts = {}

    for class_name, label in classes.items():
        images_dir = RAW_DIR / class_name / "images"
        if not images_dir.exists():
            print(f"[WARN] Dossier absent : {images_dir}", flush=True)
            continue

        files = sorted(images_dir.glob("*.png"))
        if max_n:
            files = files[:max_n]

        print(f"[INFO] Chargement {len(files)} images — {class_name}", flush=True)
        loaded = 0
        for f in files:
            try:
                img = Image.open(f).convert("L").resize((img_w, img_h))
                arr = np.array(img, dtype="float32")
                arr = (arr / 127.5) - 1.0          # normalise vers [-1, 1]
                X.append(arr.reshape(img_h, img_w, 1))
                y.append(label)
                loaded += 1
            except Exception as e:
                print(f"[WARN] {f.name}: {e}", flush=True)

        counts[class_name] = loaded

    return np.array(X, dtype="float32"), np.array(y, dtype="int32"), counts


def main() -> None:
    params = load_params()
    print("[INFO] Prétraitement démarré", flush=True)

    X, y, counts = load_images(params)
    print(f"[INFO] Total : {len(X)} images", flush=True)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=params["test_split"],
        stratify=y,
        random_state=params["random_seed"],
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(OUT_DIR / "X_train.npy", X_train)
    np.save(OUT_DIR / "X_test.npy",  X_test)
    np.save(OUT_DIR / "y_train.npy", y_train)
    np.save(OUT_DIR / "y_test.npy",  y_test)

    stats = {
        "total": int(len(X)),
        "train": int(len(X_train)),
        "test":  int(len(X_test)),
        "classes": counts,
        "img_size": params["img_size"],
    }
    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"[INFO] Train={len(X_train)}  Test={len(X_test)}", flush=True)
    print(f"[INFO] Sauvegardé dans {OUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
