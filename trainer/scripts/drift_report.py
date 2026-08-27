"""US-20 — Rapport Evidently de dérive (PSI + Jensen-Shannon).

Lit  : data/models/classification.keras + data/processed/X_train.npy (référence)
       + log-service GET /v1/logs (scores de prédiction "production" loggés
       par backend/app/api/predict.py via le logger TELEMETRY_LOGGER_NAME)
Écrit: outputs/drift/report.html

Script manuel (pas un stage DVC) : son entrée "production" dépend de
l'état runtime du log-service, non reproductible par `dvc repro`.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import tensorflow as tf
from evidently.metric_preset import DataDriftPreset
from evidently.metrics import ColumnDriftMetric
from evidently.report import Report

REPO_ROOT  = Path(__file__).parent.parent.parent
MODELS_DIR = REPO_ROOT / "data" / "models"
PROCESSED  = REPO_ROOT / "data" / "processed"
DRIFT_DIR  = REPO_ROOT / "outputs" / "drift"

# Ordre et orthographe doivent correspondre à backend/app/config.py::class_names
# (ordre de sortie du modèle) — pas à trainer/scripts/evaluate.py::CLASS_NAMES,
# qui sert uniquement à l'affichage de la matrice de confusion, pas au contrat API.
CLASS_NAMES = ["COVID", "Lung_Opacity", "Normal", "Viral_Pneumonia"]

TELEMETRY_LOGGER_NAME = "app.predict.telemetry"
PSI_ALERT_THRESHOLD = 0.2
REFERENCE_SAMPLE_SIZE = 500

LOG_SERVICE_BASE_URL = os.getenv("LOG_SERVICE_BASE_URL", "http://localhost:5002")


def _fetch_production_scores() -> pd.DataFrame:
    """Récupère les scores de prédiction loggés en "production" depuis log-service."""
    response = requests.get(
        f"{LOG_SERVICE_BASE_URL}/v1/logs",
        params={"service": "backend", "limit": 1000},
        timeout=10,
    )
    response.raise_for_status()
    entries = response.json()["entries"]
    rows = [
        entry["extra"]["scores"]
        for entry in entries
        if entry.get("logger") == TELEMETRY_LOGGER_NAME and entry.get("extra")
    ]
    if not rows:
        sys.exit(
            "[ERREUR] Aucune prédiction loggée trouvée sur le log-service — "
            "rejouer des requêtes /predict avant de générer le rapport."
        )
    return pd.DataFrame(rows)


def _reference_scores() -> pd.DataFrame:
    """Distribution de référence : scores du modèle sur un échantillon de train."""
    model = tf.keras.models.load_model(MODELS_DIR / "classification.keras")
    x_train = np.load(PROCESSED / "X_train.npy")
    sample = x_train[:REFERENCE_SAMPLE_SIZE]
    predictions = model.predict(sample, verbose=0)
    return pd.DataFrame(predictions, columns=CLASS_NAMES)


def main() -> None:
    """Génère outputs/drift/report.html comparant scores prod vs référence train."""
    print("[INFO] Chargement distribution de référence (train)...", flush=True)
    reference = _reference_scores()

    print(f"[INFO] Récupération scores prod depuis {LOG_SERVICE_BASE_URL}...",
          flush=True)
    current = _fetch_production_scores()
    current = current.reindex(columns=reference.columns, fill_value=0.0)

    print(
        f"[INFO] Référence: {len(reference)} images | Prod: {len(current)} prédictions",
        flush=True,
    )

    report = Report(metrics=[
        DataDriftPreset(stattest="psi", stattest_threshold=PSI_ALERT_THRESHOLD),
        *[
            ColumnDriftMetric(column_name=col, stattest="jensenshannon")
            for col in reference.columns
        ],
    ])
    report.run(reference_data=reference, current_data=current)

    DRIFT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DRIFT_DIR / "report.html"
    report.save_html(str(report_path))

    dataset_drift = report.as_dict()["metrics"][0]["result"]["dataset_drift"]
    print(f"[INFO] Dérive détectée (PSI > {PSI_ALERT_THRESHOLD}) : {dataset_drift}",
          flush=True)
    print(f"[INFO] Rapport  → {report_path}", flush=True)


if __name__ == "__main__":
    main()
