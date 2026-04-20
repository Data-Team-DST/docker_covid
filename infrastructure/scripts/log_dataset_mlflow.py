#!/usr/bin/env python3
"""
log_dataset_mlflow.py — Enregistre les métadonnées DVC du dataset QualiPSO dans MLflow.

Usage :
    python scripts/log_dataset_mlflow.py

Crée un run MLflow dans l'expérience "dataset-ingestion" avec :
- Nombre de fichiers, taille totale, hash DVC
- Répartition par type (.docx, .doc, .pdf, .xlsx, ...)
- Tags sprint/US pour traçabilité
"""
import os
import yaml
from pathlib import Path
from collections import Counter

import mlflow

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data-service" / "data"
DVC_FILE = ROOT / "data-service" / "data.dvc"
MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", f"sqlite:///{ROOT}/mlflow.db")

mlflow.set_tracking_uri(MLFLOW_URI)
mlflow.set_experiment("dataset-ingestion")

# Lecture métadonnées DVC
with open(DVC_FILE) as f:
    dvc_meta = yaml.safe_load(f)
dvc_out = dvc_meta["outs"][0]

# Stats fichiers
files = list(DATA_DIR.glob("*"))
files = [f for f in files if f.is_file()]
ext_counter = Counter(f.suffix.lower() for f in files)
total_size_mb = sum(f.stat().st_size for f in files) / 1024 / 1024

with mlflow.start_run(run_name="QualiPSO-dataset-v1"):
    # Paramètres dataset
    mlflow.log_params({
        "dataset_name": "QualiPSO",
        "dvc_hash": dvc_out["md5"],
        "nfiles": dvc_out["nfiles"],
        "size_bytes": dvc_out["size"],
        "sprint": "S1",
        "user_story": "US-01",
    })

    # Métriques
    mlflow.log_metrics({
        "total_files": len(files),
        "total_size_mb": round(total_size_mb, 2),
        "n_docx": ext_counter.get(".docx", 0),
        "n_doc": ext_counter.get(".doc", 0),
        "n_pdf": ext_counter.get(".pdf", 0),
        "n_xlsx": ext_counter.get(".xlsx", 0),
        "n_pptx": ext_counter.get(".pptx", 0) + ext_counter.get(".ppsx", 0) + ext_counter.get(".ppt", 0),
    })

    # Tags traçabilité
    mlflow.set_tags({
        "data_source": "QualiPSO ZIP",
        "dvc_remote": "/home/oneai/dvc-storage",
        "stage": "ingestion",
    })

    # Résumé répartition types
    summary = "\n".join(f"{ext or 'sans ext'}: {n}" for ext, n in ext_counter.most_common())
    mlflow.log_text(summary, "file_types_breakdown.txt")

    run_id = mlflow.active_run().info.run_id
    print(f"\n✅ Run MLflow créé : {run_id}")
    print(f"   Fichiers : {len(files)} ({round(total_size_mb, 1)} MB)")
    print(f"   Hash DVC : {dvc_out['md5']}")
    print(f"   → Visible dans MLflow UI > Experiments > dataset-ingestion")
