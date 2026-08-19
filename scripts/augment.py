"""Stage DVC 1/4 — Data augmentation.

Lit  : data/raw/COVID-19_Radiography_Dataset/{classe}/{images,masks}/
Écrit: data/augmented/{classe}/{images,masks}/  (originaux + variantes augmentées)

Chaque image source produit 1 original inchangé + `variants_per_image` variantes
(flip/rotation/zoom/luminosité aléatoires, seedées de façon reproductible).
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "src"))

from ds_covid.augmentation import augment_pair  # noqa: E402

PARAMS_FILE = PROJECT_ROOT / "params.yaml"
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "COVID-19_Radiography_Dataset"
OUT_DIR = PROJECT_ROOT / "data" / "augmented"
STATS_FILE = PROJECT_ROOT / "outputs" / "augment_stats.json"


def load_params() -> dict:
    with open(PARAMS_FILE, encoding="utf-8") as f:
        all_params = yaml.safe_load(f)
    return all_params["augment"], all_params["preprocess"]["classes"]  # classes: {nom: label int}


def main() -> None:
    params, classes = load_params()
    variants = params["variants_per_image"]
    rotation_range = params["rotation_range"]
    zoom_range = tuple(params["zoom_range"])
    brightness_range = tuple(params["brightness_range"])
    flip_horizontal = params["flip_horizontal"]
    seed = params["random_seed"]

    print("[INFO] Data augmentation démarrée", flush=True)
    counts = {}

    for class_name, class_label in classes.items():
        images_dir = RAW_DIR / class_name / "images"
        masks_dir = RAW_DIR / class_name / "masks"
        if not images_dir.exists():
            print(f"[WARN] Dossier absent : {images_dir}", flush=True)
            continue

        out_images_dir = OUT_DIR / class_name / "images"
        out_masks_dir = OUT_DIR / class_name / "masks"
        out_images_dir.mkdir(parents=True, exist_ok=True)
        out_masks_dir.mkdir(parents=True, exist_ok=True)

        files = sorted(images_dir.glob("*.png"))
        print(f"[INFO] Augmentation {len(files)} images — {class_name}", flush=True)
        written = 0

        for idx, f in enumerate(tqdm(files, desc=f"Augment {class_name}")):
            img = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
            if img is None:
                print(f"[WARN] {f.name}: image illisible", flush=True)
                continue

            mask_path = masks_dir / f.name
            mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE) if mask_path.exists() else None

            # Original inchangé
            cv2.imwrite(str(out_images_dir / f.name), img)
            if mask is not None:
                cv2.imwrite(str(out_masks_dir / f.name), mask)
            written += 1

            # Variantes augmentées, seedées par (seed, classe, index, variante) pour la reproductibilité
            for i in range(variants):
                rng = np.random.default_rng([seed, class_label, idx, i])
                img_aug, mask_aug = augment_pair(
                    img, mask, rng,
                    rotation_range=rotation_range,
                    zoom_range=zoom_range,
                    brightness_range=brightness_range,
                    flip_horizontal=flip_horizontal,
                )
                out_name = f"{f.stem}_aug{i}{f.suffix}"
                cv2.imwrite(str(out_images_dir / out_name), img_aug)
                if mask_aug is not None:
                    cv2.imwrite(str(out_masks_dir / out_name), mask_aug)
                written += 1

        counts[class_name] = written

    stats = {
        "total_images": sum(counts.values()),
        "per_class": counts,
        "variants_per_image": variants,
    }
    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"[INFO] Total images écrites : {sum(counts.values())}", flush=True)
    print(f"[INFO] Sauvegardé dans {OUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
