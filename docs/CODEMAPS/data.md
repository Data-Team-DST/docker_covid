<!-- Généré : 2026-08-24 | Fichiers scannés : 6 (dvc.yaml, params.yaml, data-service router) | ~350 tokens -->

# Data — pipeline DVC + data-service

Pas de base de données applicative (Postgres = backend MLflow uniquement, aucun schéma
métier). Les "données" du projet sont : le dataset image versionné DVC + le pipeline de
transformation + les endpoints `data-service` qui exposent l'un et l'autre en HTTP.

## Pipeline DVC (`dvc.yaml`)

```
augment      python trainer/scripts/augment.py
             deps: data/raw, trainer/scripts/augment.py, trainer/src/ds_covid/augmentation.py
             outs: data/augmented

preprocess   python trainer/scripts/preprocess.py
             deps: data/augmented, trainer/scripts/preprocess.py, trainer/src/ds_covid/preprocessing.py
             outs: data/processed/{X,y}_{train,test}.npy

train        (voir dvc.yaml — modèle + protocole intégrés depuis train.ipynb cette semaine)

evaluate     trainer/scripts/evaluate.py
```

Paramètres : `params.yaml` (CLAHE, split, seed, classes — paramétrable depuis 2026-08-24).

## Dataset

`data/raw.dvc` — 42 335 fichiers, 806 MB, hash `050075f5...`. Remote DVC : `minio`
(`s3://dvcstore`, `http://localhost:9000`).

## data-service — routes `/v1/*`

```
GET  /data/stats     tags=[data]   statistiques dataset (cache)
GET  /data/image     tags=[data]   sert une image (path traversal testé, voir tests)
GET  /data/search     tags=[data]   recherche dans le dataset
GET  /dvc/status      tags=[dvc]
GET  /dvc/remotes     tags=[dvc]
POST /dvc/pull        tags=[dvc]
POST /dvc/push        tags=[dvc]
POST /dvc/repro       tags=[dvc]    relance le pipeline DVC via subprocess
```

`dvc/*` exécute `dvc` en `subprocess.run` — pas de binaire `dvc` réel requis pour les tests
(mocké, voir `data-service/tests/test_router.py`).

## MLflow / Postgres / MinIO

- Postgres (`mlflow` DB) : backend de tracking MLflow uniquement.
- MinIO : double rôle — artifacts MLflow (bucket `mlflow`) + remote DVC (bucket `dvcstore`).
