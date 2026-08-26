"""Stage DVC — Prétraitement des paires (image, mask) pour l'entraînement du U-Net.

Lit  : data/augmented/{train,test}/{classe}/{images,masks}/  (même sortie que le
       stage `augment` utilisé par le pipeline de classification — la segmentation
       réutilise donc directement les mêmes paires image/mask, déjà augmentées et
       splittées train/test)
Écrit: data/processed/segmentation/{X,M}_{train,test}.npy

Contrairement à deep_learning.preprocessing.process_single_image (pipeline classification),
on ne masque/crop/CLAHE PAS l'image ici : le mask est la cible à prédire, pas une
entrée du preprocessing.
"""
import json
import sys
from pathlib import Path

import yaml
from numpy.lib.format import open_memmap
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "trainer"))

from deep_learning.segmentation import collect_pairs, load_pair  # noqa: E402

PARAMS_FILE = PROJECT_ROOT / "params.yaml"
AUGMENTED_DIR = PROJECT_ROOT / "data" / "augmented"
OUT_DIR = PROJECT_ROOT / "data" / "processed" / "segmentation"
STATS_FILE = PROJECT_ROOT / "outputs" / "preprocess_segmentation_stats.json"


def load_params() -> dict:
    with open(PARAMS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)["preprocess"]


def write_split(img_paths, mask_paths, img_size: int, out_x_path: Path, out_m_path: Path, desc: str) -> None:
    """Prétraite une liste de paires et les écrit directement sur disque (memmap),
    sans jamais garder l'ensemble des images en RAM (même contrainte que preprocess.py)."""
    X = open_memmap(out_x_path, mode="w+", dtype="float32", shape=(len(img_paths), img_size, img_size, 1))
    M = open_memmap(out_m_path, mode="w+", dtype="float32", shape=(len(img_paths), img_size, img_size, 1))

    kept = 0
    for i, (img_path, mask_path) in enumerate(tqdm(list(zip(img_paths, mask_paths)), desc=desc)):
        try:
            img, mask = load_pair(img_path, mask_path, img_size)
            X[i] = img
            M[i] = mask
            kept += 1
        except Exception as e:
            print(f"[WARN] {img_path.name}: {e}", flush=True)

    X.flush()
    M.flush()
    return kept


def main() -> None:
    params = load_params()
    img_h, img_w = params["img_size"]
    assert img_h == img_w, "Le U-Net attend des images carrées"

    print("[INFO] Prétraitement segmentation démarré", flush=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    stats = {}
    for split in ("train", "test"):
        img_paths, mask_paths = collect_pairs(AUGMENTED_DIR / split, params["classes"])
        print(f"[INFO] {split} : {len(img_paths)} paires image/mask", flush=True)
        kept = write_split(
            img_paths, mask_paths, img_h,
            OUT_DIR / f"X_{split}.npy", OUT_DIR / f"M_{split}.npy", split.capitalize(),
        )
        stats[split] = kept

    stats["img_size"] = params["img_size"]
    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"[INFO] Train={stats['train']}  Test={stats['test']}", flush=True)
    print(f"[INFO] Sauvegardé dans {OUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
