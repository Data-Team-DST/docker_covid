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

# 2. Lancer le setup (choisir Développeur ou Utilisateur)
./setup.sh
```

`setup.sh` vous guidera interactivement :
- **[1] Développeur** — Docker + venv IDE optionnel. Construit les images localement.
- **[2] Utilisateur** — Docker uniquement. Lance la stack telle quelle.

> **Pré-requis** : [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et démarré.
> WSL2 : activer la distro dans Docker Desktop > Settings > Resources > WSL Integration.

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

| Service   | URL                          | Description                       |
|-----------|------------------------------|-----------------------------------|
| API       | http://localhost:8000        | Backend FastAPI — `/docs` Swagger |
| Streamlit | http://localhost:8501        | Frontend multi-pages              |
| Health    | http://localhost:8000/health | Statut API + modèle               |
| MLflow    | http://localhost:5000        | Tracking (Phase 2)                |
| MinIO     | http://localhost:9001        | Object storage (Phase 2)          |

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
│   ├── tests/unit/          # Tests unitaires (pytest)
│   └── requirements.txt
├── frontend/                # Streamlit multi-pages
│   ├── streamlit_app.py
│   └── page/                # 01_accueil … 07_conclusion
├── src/                     # Code ML DS_COVID (training, features, interprétabilité)
├── docker/                  # Dockerfiles par service
│   ├── backend/
│   └── streamlit/
├── data/
│   └── models/              # ← Placer le fichier .keras ici
├── requirements/
│   ├── local.txt            # Dev local (sans tensorflow)
│   └── base.txt / streamlit.txt / trainer.txt
├── docker-compose.yml       # Stack complète
├── setup.sh                 # LANCER EN PREMIER
├── start_local.sh           # Backend + frontend sans Docker (dev avancé)
├── Makefile                 # Toutes les commandes
├── .env.example             # Template — copié automatiquement par setup.sh
└── .github/workflows/
    └── cicd.yml             # CI/CD : lint → tests → SonarCloud → build GHCR
```

---

## Configuration

`setup.sh` copie automatiquement `.env.example` → `.env`.
Adapter si besoin :

```env
MODEL_PATH=data/models/best_model.keras   # nom réel du fichier .keras
```

**Sans modèle** : l'API démarre quand même.
`/health` répond `model_loaded: false`, `/predict` retourne 503.

---

## Tests

```bash
make test
# ou directement dans Docker :
docker compose run --rm backend pytest tests/ --cov=app -v
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
| **1** | Env reproductible, API, CI/CD | 13/03/2026 | En cours    |
| **2** | Microservices, MLflow, DVC    | 20/03/2026 | A faire     |
| **3** | CI/CD complet, Kubernetes     | 24/04/2026 | A faire     |
| **4** | Monitoring, Evidently, Drift  | 01/09/2026 | A faire     |
| **Soutenance** | Présentation finale | 04/09/2026 | A faire |

---

## Contexte

Ce projet part du travail Data Science réalisé en année précédente (repo [`DS_COVID`](https://github.com/Data-Team-DST/DS_COVID)) :
modélisation CNN + InceptionV3, preprocessing, SHAP/LIME, Streamlit multi-pages.
L'objectif MLOps est d'industrialiser ce pipeline : versioning, API, CI/CD, monitoring.
