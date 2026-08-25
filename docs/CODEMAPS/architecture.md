<!-- Généré : 2026-08-24 | Fichiers scannés : ~30 (config/entrées) | ~450 tokens -->

# Architecture — DS_COVID MLOps

Microservices Python, communication **HTTP uniquement** entre services (zéro import direct,
règle R8 `.claude/rules/python/import_cascade.md`).

```
┌──────────────┐   HTTP    ┌──────────────┐   HTTP    ┌──────────────┐
│  frontend     │──────────▶│  backend      │           │ data-service  │
│  Streamlit    │           │  FastAPI      │           │  FastAPI      │
│  :8501        │           │  :8000        │           │  :5001        │
└──────────────┘           └──────┬───────┘           └──────┬───────┘
                                    │  HTTP                     │  HTTP
                                    ▼                            ▼
                            ┌──────────────┐           ┌──────────────┐
                            │ log-service   │◀──────────│  (DVC pull/   │
                            │ FastAPI :5002 │  logs     │   push/status)│
                            └──────────────┘           └──────────────┘

  MLflow :5000 ── Postgres :5432 (backend MLflow) ── MinIO :9000/9001 (artifacts + DVC remote)
```

## Services

| Service | Port | Rôle | Entrée |
|---|---|---|---|
| backend | 8000 | Inférence ML (classification radios) | `backend/app/main.py` |
| data-service | 5001 | DVC pull/push/status, stats données | `data-service/src/data_service/main.py` |
| log-service | 5002 | Agrégateur logs JSON centralisé | `log-service/` (non détaillé — hors scope scan) |
| frontend | 8501 | UI Streamlit multi-pages (7 pages) | `frontend/streamlit_app.py` |
| dashboard | 5050 | Backlog agile + data explorer (outil interne) | `dashboard/` |
| mlflow | 5000 | Tracking expériences ML | image officielle |
| postgres | 5432 | Backend MLflow | image officielle |
| minio | 9000/9001 | Artifacts MLflow + remote DVC | image officielle |
| trainer | 8888 | Conteneur d'entraînement (notebooks) | `infrastructure/docker/trainer/` |

Déclarés dans `infrastructure/docker-compose.yml` (9 services + volumes `postgres-data`,
`minio-data` + réseau `covid-net`).

## Frontières de service (zéro import Python direct)

- `backend/`, `data-service/`, `log-service/` communiquent uniquement via `/health`, `/v1/...`,
  `/api/v1/...`.
- `shared/logging_config.py` est la seule exception : module utilitaire pur importé par tous
  les services (logging JSON structuré), pas de logique métier.

## Pipeline ML (hors services, orchestré par DVC)

`dvc.yaml` : `augment` → `preprocess` → `train` → `evaluate` (voir `data.md`).

## Déploiement

- Local : `infrastructure/docker-compose.yml` (dev complet)
- K8s (Phase 3, non déployé en prod à ce jour) : `infrastructure/kubernetes/*.yaml`
  (namespace `ds-covid`, ingress nginx routant `/`→streamlit, `/api`→backend, `/mlflow`→mlflow)
- CI/CD : `.github/workflows/cicd.yml` — lint → test → sonarcloud → build (GHCR matrix) →
  deploy smoke-test → summary
