"""Stage DVC 2/4 — Prétraitement des images.

Lit  : data/augmented/{train,test}/{classe}/{images,masks}/  (sortie du stage augment,
       déjà splittée — le split train/test est fait dans augment.py, avant augmentation)
Écrit: data/processed/{X,y}_{train,test}.npy

Pipeline par image (voir ds_covid.preprocessing.process_single_image) :
  denoising (optionnel) → masking + crop poumons (optionnel) → CLAHE (optionnel) → resize
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml
from numpy.lib.format import open_memmap
from tqdm import tqdm

TRAINER_ROOT = Path(__file__).parent.parent
REPO_ROOT = TRAINER_ROOT.parent
sys.path.insert(0, str(TRAINER_ROOT / "src"))

from ds_covid.preprocessing import process_single_image  # noqa: E402

PARAMS_FILE = REPO_ROOT / "params.yaml"
AUGMENTED_DIR = REPO_ROOT / "data" / "augmented"
OUT_DIR = REPO_ROOT / "data" / "processed"
STATS_FILE = REPO_ROOT / "outputs" / "preprocess_stats.json"


def load_params() -> dict:
    with open(PARAMS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)["preprocess"]


def list_files(split_dir: Path, classes: dict) -> tuple[list[Path], list[int], dict]:
    """Liste les fichiers d'un split (train ou test), sans charger d'image en mémoire."""
    paths, labels = [], []
    counts = {}

    for class_name, label in classes.items():
        images_dir = split_dir / class_name / "images"
        if not images_dir.exists():
            print(f"[WARN] Dossier absent : {images_dir}", flush=True)
            continue

        files = sorted(images_dir.glob("*.png"))
        paths.extend(files)
        labels.extend([label] * len(files))
        counts[class_name] = len(files)

    return paths, labels, counts


def write_split(
    paths: list[Path],
    labels: list[int],
    params: dict,
    out_x_path: Path,
    out_y_path: Path,
    desc: str,
) -> None:
    """Prétraite une liste de fichiers et les écrit directement sur disque (memmap),
    sans jamais garder l'ensemble des images en RAM — indispensable vu le volume
    (dizaines de milliers d'images après augmentation, largement supérieur à la RAM
    disponible si on accumulait tout dans un np.array avant sauvegarde)."""
    img_h, img_w = params["img_size"]
    masking = params.get("masking", False)
    cropping = params.get("cropping", False) and masking
    denoising_method = params.get("denoising_method")
    clahe_processor = (
        cv2.createCLAHE(
            clipLimit=params.get("clahe_clip_limit", 2.0),
            tileGridSize=tuple(params.get("clahe_tile_grid_size", [8, 8])),
        )
        if params.get("clahe")
        else None
    )

    X = open_memmap(out_x_path, mode="w+", dtype="float32", shape=(len(paths), img_h, img_w, 1))
    y = np.array(labels, dtype="int32")

    for i, f in enumerate(tqdm(paths, desc=desc)):
        try:
            masks_dir = f.parent.parent / "masks"
            mask_path = masks_dir / f.name if masking else None
            arr = process_single_image(
                img_path=f,
                mask_path=mask_path,
                cropping=cropping,
                denoising_method=denoising_method,
                clahe_processor=clahe_processor,
                target_size=img_w,
            )
            arr = arr.astype("float32")
            # [-1, 1] plutôt que minmax [0, 1] (exploré dans train.ipynb) : doit
            # rester identique à backend/app/features/preprocessing.py::preprocess_image,
            # qui applique exactement (arr / 127.5) - 1.0 à l'inférence — un écart ici
            # provoquerait un train/serving skew (déjà rencontré une fois sur ce projet).
            arr = (arr / 127.5) - 1.0          # normalise vers [-1, 1]
            X[i] = arr.reshape(img_h, img_w, 1)
        except Exception as e:
            print(f"[WARN] {f.name}: {e}", flush=True)

    X.flush()
    np.save(out_y_path, y)


def main() -> None:
    params = load_params()
    print("[INFO] Prétraitement démarré", flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    train_paths, train_labels, train_counts = list_files(AUGMENTED_DIR / "train", params["classes"])
    print(f"[INFO] Train : {len(train_paths)} images", flush=True)
    write_split(train_paths, train_labels, params, OUT_DIR / "X_train.npy", OUT_DIR / "y_train.npy", "Train")

    test_paths, test_labels, test_counts = list_files(AUGMENTED_DIR / "test", params["classes"])
    print(f"[INFO] Test : {len(test_paths)} images", flush=True)
    write_split(test_paths, test_labels, params, OUT_DIR / "X_test.npy", OUT_DIR / "y_test.npy", "Test")

    stats = {
        "total": len(train_paths) + len(test_paths),
        "train": len(train_paths),
        "test":  len(test_paths),
        "train_per_class": train_counts,
        "test_per_class": test_counts,
        "img_size": params["img_size"],
    }
    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"[INFO] Train={len(train_paths)}  Test={len(test_paths)}", flush=True)
    print(f"[INFO] Sauvegardé dans {OUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
