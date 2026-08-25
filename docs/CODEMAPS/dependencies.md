<!-- Généré : 2026-08-24 | Fichiers scannés : 8 (requirements*.txt/.in) | ~300 tokens -->

# Dependencies — services externes & third-party

## Services externes (infra)

| Service | Rôle | Où |
|---|---|---|
| MinIO | Object storage — artifacts MLflow + remote DVC | docker-compose, K8s |
| Postgres 16 | Backend MLflow (tracking DB) | docker-compose, K8s |
| GHCR (ghcr.io) | Registre d'images Docker (CI publie ici) | `.github/workflows/cicd.yml` |
| SonarCloud | Analyse qualité/coverage (`SONAR_TOKEN` en secret repo) | CI |
| DagsHub (`dagshub.com`) | Remote S3 distant pour sync DVC (`REMOTE_S3_ENDPOINT`) | `.env` |

## Librairies clés par service (versions pinnées, lock files hash-verrouillés)

**backend** : `fastapi`, `pydantic-settings`, `slowapi` (rate limit), `tensorflow`/`keras`
(modèle CNN), `pillow`, `numpy`.

**data-service** : `fastapi`, `dvc[s3]`, `boto3`/`s3fs` (via dvc[s3]).

**frontend** : `streamlit`, `plotly`, `pandas`, `pillow`. `kagglehub` (téléchargement dataset).

**ML pipeline** (`backend/src/ds_covid/`) : `tensorflow`, `scikit-learn`, `opencv`/`albumentations`
selon les stages (augment/preprocess).

## Fichiers de lock

`requirements.in` (source, top-level) → `requirements.txt` (pip-compile --generate-hashes,
graphe complet + hashs). 4 paires : `backend/requirements-dev.{in,txt}`,
`data-service/{requirements,dev-requirements}.{in,txt}`, `frontend/requirements.{in,txt}`.
CI installe via `pip install --require-hashes -r ...` (voir `.github/workflows/cicd.yml`).

## Registres d'images publiées (GHCR, matrix CI)

```
ghcr.io/data-team-dst/covid-xray-backend
ghcr.io/data-team-dst/covid-xray-streamlit   (dépend de covid-xray-base)
ghcr.io/data-team-dst/covid-xray-data-service
```
