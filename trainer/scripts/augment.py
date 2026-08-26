"""Stage DVC 1/4 — Split train/test + data augmentation.

Lit  : data/raw/COVID-19_Radiography_Dataset/{classe}/{images,masks}/
Écrit: data/augmented/{train,test}/{classe}/{images,masks}/

Le split train/test est fait ICI, sur les images brutes, avant toute
augmentation — seul le train est augmenté (original + variantes), le test
ne contient que les originaux. Sinon une image et sa variante augmentée
(quasi-identiques) pourraient se retrouver de part et d'autre du split,
et le modèle "reconnaîtrait" en test des quasi-doublons vus à l'entraînement.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml
from sklearn.model_selection import train_test_split
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "trainer"))

from deep_learning.augmentation import augment_pair  # noqa: E402

PARAMS_FILE = PROJECT_ROOT / "params.yaml"
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "COVID-19_Radiography_Dataset"
OUT_DIR = PROJECT_ROOT / "data" / "augmented"
STATS_FILE = PROJECT_ROOT / "outputs" / "augment_stats.json"


def load_params() -> dict:
    with open(PARAMS_FILE, encoding="utf-8") as f:
        all_params = yaml.safe_load(f)
    return all_params["augment"], all_params["preprocess"]


def write_pair(img_path: Path, mask_path: Path, out_images_dir: Path, out_masks_dir: Path):
    """Copie une image + son mask (inchangés) vers le dossier de sortie. Renvoie (img, mask) en mémoire."""
    img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"[WARN] {img_path.name}: image illisible", flush=True)
        return None

    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE) if mask_path.exists() else None

    cv2.imwrite(str(out_images_dir / img_path.name), img)
    if mask is not None:
        cv2.imwrite(str(out_masks_dir / img_path.name), mask)
    return img, mask


def main() -> None:
    aug_params, prep_params = load_params()
    variants = aug_params["variants_per_image"]
    rotation_range = aug_params["rotation_range"]
    zoom_range = tuple(aug_params["zoom_range"])
    brightness_range = tuple(aug_params["brightness_range"])
    flip_horizontal = aug_params["flip_horizontal"]
    seed = aug_params["random_seed"]

    classes = prep_params["classes"]
    max_samples_per_class = prep_params["max_samples_per_class"]
    test_split = prep_params["test_split"]
    split_seed = prep_params["random_seed"]

    print("[INFO] Split train/test + augmentation démarrés", flush=True)
    counts = {"train": {}, "test": {}}

    for class_name, class_label in classes.items():
        images_dir = RAW_DIR / class_name / "images"
        masks_dir = RAW_DIR / class_name / "masks"
        if not images_dir.exists():
            print(f"[WARN] Dossier absent : {images_dir}", flush=True)
            continue

        files = sorted(images_dir.glob("*.png"))
        if max_samples_per_class:
            files = files[:max_samples_per_class]

        train_files, test_files = train_test_split(
            files, test_size=test_split, random_state=split_seed
        )
        print(f"[INFO] {class_name} : {len(train_files)} train / {len(test_files)} test (avant augmentation)", flush=True)

        # --- Test : originaux uniquement, jamais augmentés ---
        out_images_dir = OUT_DIR / "test" / class_name / "images"
        out_masks_dir = OUT_DIR / "test" / class_name / "masks"
        out_images_dir.mkdir(parents=True, exist_ok=True)
        out_masks_dir.mkdir(parents=True, exist_ok=True)

        written = 0
        for f in tqdm(test_files, desc=f"Test {class_name}"):
            if write_pair(f, masks_dir / f.name, out_images_dir, out_masks_dir) is not None:
                written += 1
        counts["test"][class_name] = written

        # --- Train : original + variantes augmentées ---
        out_images_dir = OUT_DIR / "train" / class_name / "images"
        out_masks_dir = OUT_DIR / "train" / class_name / "masks"
        out_images_dir.mkdir(parents=True, exist_ok=True)
        out_masks_dir.mkdir(parents=True, exist_ok=True)

        written = 0
        for idx, f in enumerate(tqdm(train_files, desc=f"Train {class_name}")):
            result = write_pair(f, masks_dir / f.name, out_images_dir, out_masks_dir)
            if result is None:
                continue
            img, mask = result
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

        counts["train"][class_name] = written

    stats = {
        "train_total": sum(counts["train"].values()),
        "test_total": sum(counts["test"].values()),
        "train_per_class": counts["train"],
        "test_per_class": counts["test"],
        "variants_per_image": variants,
    }
    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"[INFO] Train={stats['train_total']}  Test={stats['test_total']}", flush=True)
    print(f"[INFO] Sauvegardé dans {OUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
