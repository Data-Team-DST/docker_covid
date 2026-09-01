"""Génère du trafic artificiel sur /predict avec des images du dataset tirées au hasard.

Utile pour peupler le log-service de prédictions "production" avant de lancer
`drift_report.py` (qui a besoin d'au moins quelques entrées loggées pour comparer
à la distribution de référence).

Lit  : data/raw/COVID-19_Radiography_Dataset/*/images/*.png
Écrit: rien en local — POST vers BACKEND_URL/api/v1/predict (le backend loggue
       lui-même chaque prédiction vers log-service, voir backend/app/api/predict.py)

Script manuel (pas un stage DVC), même famille que `drift_report.py`.

Usage :
    python trainer/scripts/generate_traffic.py --count 50
    python trainer/scripts/generate_traffic.py --count 200 --delay 0.2
"""
import argparse
import os
import random
import sys
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).parent.parent.parent
DATASET_DIR = REPO_ROOT / "data" / "raw" / "COVID-19_Radiography_Dataset"
CLASSES = ["COVID", "Normal", "Viral Pneumonia", "Lung_Opacity"]

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")

DEFAULT_COUNT = 50
DEFAULT_DELAY_S = 0.1
REQUEST_TIMEOUT_S = 30


def _list_images() -> list[Path]:
    """Liste toutes les images du dataset brut, toutes classes confondues."""
    images = [
        path
        for class_name in CLASSES
        for path in (DATASET_DIR / class_name / "images").glob("*.png")
    ]
    if not images:
        sys.exit(
            f"[ERREUR] Aucune image trouvée sous {DATASET_DIR} — "
            "dataset non présent localement (dvc pull requis)."
        )
    return images


def _predict_one(image_path: Path) -> tuple[bool, str]:
    """Envoie une image à /predict, retourne (succès, message court)."""
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    with image_path.open("rb") as image_file:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/predict",
            files={"file": (image_path.name, image_file, "image/png")},
            headers=headers,
            timeout=REQUEST_TIMEOUT_S,
        )
    if response.status_code != 200:
        return False, f"HTTP {response.status_code} — {response.text[:120]}"
    body = response.json()
    return True, f"{body['predicted_class']} ({body['confidence']:.0%})"


def main() -> None:
    """Tire `--count` images au hasard dans le dataset et les envoie à /predict."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT,
                         help=f"Nombre de requêtes à envoyer (défaut : {DEFAULT_COUNT})")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_S,
                         help=f"Délai entre deux requêtes, en secondes (défaut : {DEFAULT_DELAY_S})")
    parser.add_argument("--seed", type=int, default=None,
                         help="Graine aléatoire pour un tirage reproductible")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    images = _list_images()
    sample = [random.choice(images) for _ in range(args.count)]

    print(f"[INFO] {args.count} requêtes vers {BACKEND_URL}/api/v1/predict "
          f"(dataset : {len(images)} images disponibles)", flush=True)

    n_ok = 0
    for i, image_path in enumerate(sample, start=1):
        try:
            ok, message = _predict_one(image_path)
        except requests.RequestException as exc:
            ok, message = False, f"requête échouée — {exc}"
        n_ok += ok
        print(f"[{i}/{args.count}] {image_path.parent.parent.name}/{image_path.name} → {message}",
              flush=True)
        time.sleep(args.delay)

    print(f"[INFO] Terminé : {n_ok}/{args.count} requêtes réussies.", flush=True)


if __name__ == "__main__":
    main()
