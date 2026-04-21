# DS_COVID — Projet MLOps

Classification automatique de radiographies pulmonaires
(COVID-19 · Lung Opacity · Normal · Viral Pneumonia)

> **Projet MLOps** — Industrialisation du pipeline DS_COVID
> Phases 1→4 | Mars → Septembre 2026

---

## Premier démarrage (une seule fois)

```bash
# 1. Cloner le repo
git clone https://github.com/Data-Team-DST/docker_covid.git
cd docker_covid

# 2. Setup (venv, deps, .env, dossiers)
make setup
```

> **Pré-requis** : [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et démarré.
>
> **WSL2** : activer la distro dans Docker Desktop → Settings → Resources → WSL Integration.
> Sans ça, `docker` ne sera pas trouvé dans le terminal WSL.

### Commandes de dev (sans `make`)

```bash
# Depuis la racine du projet (WSL ou Git Bash)
bash infrastructure/scripts/setup.sh          # setup
bash infrastructure/scripts/check_quality.sh  # qualité
bash infrastructure/scripts/fix_style.sh      # auto-style
bash infrastructure/scripts/start_local.sh    # backend+frontend sans Docker
```

> ⚠️ Toujours utiliser des `/` (slash) et non des `\` (backslash) en WSL/bash.

---

## Commandes du quotidien

```bash
make start          # backend FastAPI seul (http://localhost:8000)
make start-all      # stack complète : backend + frontend + mlflow + minio
make stop           # arrêter tous les services
make test           # tests unitaires (dans Docker)
make lint           # vérification qualité
make fix            # auto-correction style (ruff + black + isort)
make build          # rebuilder les images
make logs           # logs backend en temps réel
```

| Service      | URL                          | Description                           |
|--------------|------------------------------|---------------------------------------|
| API          | http://localhost:8000        | Backend FastAPI — `/docs` Swagger     |
| Data Service | http://localhost:5001        | DVC pull/push/status — `/docs`        |
| Streamlit    | http://localhost:8501        | Frontend multi-pages                  |
| MLflow       | http://localhost:5000        | Tracking expériences (Phase 2)        |
| MinIO        | http://localhost:9001        | Object storage DVC + artifacts        |
| Dashboard    | http://localhost:5050        | Backlog agile + data explorer         |

### Commandes data-service

```bash
make data-start   # lance le data-service seul (port 5001)
make data-logs    # logs en direct
make data-test    # tests unitaires data-service
make data-shell   # shell dans le container
```

---

## Structure du projet

```
docker_covid/
├── backend/                 # Service FastAPI (inférence ML)
│   ├── app/
│   │   ├── main.py          # Point d'entrée FastAPI
│   │   ├── config.py        # Configuration centralisée
│   │   ├── api/             # Endpoints : /health, /predict
│   │   ├── models/          # Chargement modèle Keras
│   │   ├── features/        # Preprocessing image
│   │   └── schemas/         # Schémas Pydantic
│   ├── src/                 # Code ML DS_COVID (training, features, interprétabilité)
│   └── tests/unit/          # Tests unitaires (pytest)
├── data-service/            # Microservice DVC : pull/push/status + stats données
│   ├── src/data_service/    # FastAPI (GET /health, /v1/data/stats, /v1/dvc/*)
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                # Streamlit multi-pages
│   ├── streamlit_app.py
│   └── page/                # 01_accueil … 07_conclusion
├── dashboard/               # Dashboard agile Flask (backlog sprints + data explorer)
│   ├── app.py               # Flask — http://localhost:5050
│   ├── backlog.yaml         # Sprints DS_COVID (phases 1→4)
│   └── templates/
├── infrastructure/
│   ├── docker/              # Dockerfiles par service (backend, streamlit, trainer…)
│   ├── kubernetes/          # Manifests K8s (Phase 3)
│   ├── docker-compose.yml   # Stack complète (8 services)
│   └── scripts/             # setup.sh, check_quality.sh, fix_style.sh, start_local.sh
├── docs/                    # Architecture, SMART, backlogs, plan de base
├── data/
│   ├── raw.dvc              # 42 330 images trackées DVC (806 MB)
│   └── models/              # ← Placer le fichier .keras ici
├── requirements/
│   ├── local.txt            # Dev local (sans tensorflow)
│   └── base.txt / streamlit.txt / trainer.txt
├── Makefile                 # Toutes les commandes (`make help`)
├── .env.example             # Template — copié automatiquement par make setup
└── .github/workflows/
    └── cicd.yml             # CI/CD : lint → tests → SonarCloud → build GHCR
```

---

## Configuration

`make setup` copie automatiquement `.env.example` → `.env`.
Adapter si besoin :

```env
MODEL_PATH=data/models/best_model.keras   # nom réel du fichier .keras
```

**Sans modèle** : l'API démarre quand même.
`/health` répond `model_loaded: false`, `/predict` retourne 503.

---

## Pipeline DVC — `dvc repro`

Le pipeline ML est défini dans [`dvc.yaml`](dvc.yaml) avec 3 stages :

```
data/raw  →  preprocess  →  data/processed/  →  train  →  data/models/covid_model.keras
                                                              ↓
                                                          evaluate  →  outputs/evaluation_report.json
```

### Lancer le pipeline complet

```bash
# Prérequis : data/raw/ pullé (make data-start puis DVC pull via dashboard)
dvc repro          # rejoue uniquement les stages dont les dépendances ont changé
dvc repro --force  # rejoue tout sans vérifier le cache
```

### Paramètres ([`params.yaml`](params.yaml))

```yaml
preprocess:
  img_size: [256, 256]
  max_samples_per_class: null   # null = toutes les images (42 330)
  test_split: 0.2

train:
  epochs: 10
  batch_size: 32
  learning_rate: 0.001
```

Modifier `params.yaml` → `dvc repro` rejoue uniquement les stages impactés.

### Résultats

| Fichier | Contenu |
|---|---|
| `outputs/metrics.json` | val_accuracy, val_loss |
| `outputs/evaluation_report.json` | accuracy, matrice de confusion, rapport par classe |
| `outputs/preprocess_stats.json` | nb images par classe, split train/test |

```bash
dvc metrics show   # affiche outputs/metrics.json
dvc params diff    # compare les params entre commits
```

---

## Tests

```bash
make test
# ou directement dans Docker :
docker compose -f infrastructure/docker-compose.yml run --rm backend pytest tests/ --cov=app -v
```

Coverage cible Phase 1 : >= 40 %

---

## API — Endpoints

### `GET /health`
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_version": "1.0.0",
  "classes": ["COVID", "Lung_Opacity", "Normal", "Viral_Pneumonia"]
}
```

### `POST /api/v1/predict`
- **Input** : image JPEG/PNG (`multipart/form-data`)
- **Output** :
```json
{
  "predicted_class": "COVID",
  "confidence": 0.92,
  "scores": {"COVID": 0.92, "Lung_Opacity": 0.04, "Normal": 0.03, "Viral_Pneumonia": 0.01},
  "latency_ms": 245.3
}
```

Documentation interactive : http://localhost:8000/docs

---

## Roadmap MLOps

| Phase | Contenu                       | Deadline   | Status      |
|-------|-------------------------------|------------|-------------|
| **1** | Env reproductible, API, CI/CD | 13/03/2026 | ✅ Livré    |
| **2** | Microservices, MLflow, DVC    | 20/03/2026 | ✅ Livré    |
| **3** | CI/CD complet, Kubernetes     | 24/04/2026 | A faire     |
| **4** | Monitoring, Evidently, Drift  | 01/09/2026 | A faire     |
| **Soutenance** | Présentation finale | 04/09/2026 | A faire |

---

## Contexte

Ce projet part du travail Data Science réalisé en année précédente (repo [`DS_COVID`](https://github.com/Data-Team-DST/DS_COVID)) :
modélisation CNN + InceptionV3, preprocessing, SHAP/LIME, Streamlit multi-pages.
L'objectif MLOps est d'industrialiser ce pipeline : versioning, API, CI/CD, monitoring.
