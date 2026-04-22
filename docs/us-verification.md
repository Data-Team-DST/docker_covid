# Vérification des User Stories — DS_COVID MLOps

Pour chaque US terminée : ce qui a été fait + comment vérifier sans ambiguïté.

---

## S1 — Fondations & API d'inférence

### US-01 · Repo Git unifié + structure microservices ✅
**Fait :** Fusion DS_COVID + docker_covid, structure `backend/`, `frontend/`, `infrastructure/`, branches `main / dev / feature/*`.  
**Vérifier :**
```bash
git log --oneline --graph origin/main | head -10
ls backend/ frontend/ infrastructure/ shared/
```

---

### US-02 · API FastAPI GET /health + POST /predict ✅
**Fait :** `/health` retourne `status + model_loaded`, `/predict` accepte une image multipart et retourne `class + confidence + scores`.  
**Vérifier :**
```bash
make start-docker          # ou ./start_local.sh
curl http://localhost:8000/health
curl -X POST http://localhost:8000/predict \
     -F "file=@data/raw/COVID-19_Radiography_Dataset/COVID/images/COVID-1.png"
# → {"class":"COVID","confidence":0.97,"scores":{...}}
```

---

### US-03 · Docker Compose + images GHCR ✅
**Fait :** `docker-compose.yml` (7 services). Images publiées sur GHCR via CI. Tags `sha-*`, branche, `latest` sur main.  
**Vérifier :**
```bash
make start-docker
docker ps   # → backend, frontend, mlflow, postgres, minio, data-service, log-service UP
# Puis sur https://github.com/orgs/Data-Team-DST/packages : voir les 3 images taguées
```

---

### US-04 · Tests unitaires ≥ 40% coverage ✅
**Fait :** 9 tests backend (`preprocessing`, `schemas`, `api`). Coverage ≥ 40% mesurée par `pytest-cov`. CI vert.  
**Vérifier :**
```bash
make test
# → 9 passed, coverage ≥ 40%
# Ou regarder le badge SonarCloud / artefact be-cov.xml dans GitHub Actions
```

---

### US-05 · DVC initialisé + remote MinIO ✅
**Fait :** `data/raw.dvc` tracke 42 330 images (806 MB). Remote MinIO `minio:9000` configuré. Push/pull fonctionnels depuis les containers.  
**Vérifier :**
```bash
make start-docker
# Depuis le dashboard → onglet DVC → bouton "Pull" → doit retourner 200
dvc status   # → "Data and pipelines are up to date"
```

---

## S2 — Microservices, MLflow & Versioning

### US-06 · MLflow Tracking Server containerisé ✅
**Fait :** Service `mlflow` dans `docker-compose.yml` (port 5000). Backend PostgreSQL, artifacts sur MinIO.  
**Vérifier :**
```bash
make start-docker
open http://localhost:5000   # UI MLflow → onglet Experiments
```

---

### US-07 · Architecture microservices complète ✅
**Fait :** 7 services dans `infrastructure/docker-compose.yml`. `data-service` sur :5001, `log-service` sur :5002. `shared/` monté en lecture seule dans chaque service.  
**Vérifier :**
```bash
make start-docker
curl http://localhost:5001/health   # data-service
curl http://localhost:5002/health   # log-service → {"status":"healthy","buffered_entries":N}
```

---

### US-08 · DVC pipeline reproductible ✅
**Fait :** `dvc.yaml` avec 3 stages : `preprocess → train → evaluate`. `params.yaml` pour tous les hyperparamètres. Métriques dans `outputs/metrics.json` et `outputs/evaluation_report.json`. MLflow loggé depuis `train`.  
**Vérifier :**
```bash
# Avec Docker (env officiel) :
docker compose -f infrastructure/docker-compose.yml run --rm trainer dvc repro
# → Rejoue les 3 stages, génère outputs/metrics.json
cat outputs/metrics.json   # → {"accuracy":X,"f1":X,...}

# Vérifier que les params sont pris en compte :
# Changer params.yaml (ex: epochs: 2), relancer dvc repro → seul le stage train se relance
dvc metrics show   # → tableau comparatif si plusieurs runs
```

---

### US-09 · Qualité code ✅
**Fait :** `check_quality.sh` (ruff + pylint + tests + structure + code smell, cache ×17 speedup). `check_requirements.sh` (3 catégories TOOL/IMPLICIT/ACTIVE).  
**Vérifier :**
```bash
./check_quality.sh
# → Rapport tmp/quality/report.txt, exit 0 si tout passe
./check_requirements.sh
```

---

### US-10 · Refactoring scripts ✅
**Fait :** Scripts dans `infrastructure/scripts/`. `setup.sh` détecte OS (WSL/Linux/macOS). `start_services.sh` avec `-f infrastructure/docker-compose.yml`.  
**Vérifier :**
```bash
./setup.sh --check   # → "Environment OK"
make help            # → liste toutes les cibles disponibles
```

---

## S3 — CI/CD complet & API production-ready

### US-13 · Log-service centralisé + logs JSON ✅
**Fait :** `log-service/` (FastAPI :5002). `shared/logging_config.py` utilisé par tous les services : stdout JSON + fichier rotatif `tmp/logs/{service}.log` + envoi async WARNING+ au log-service central. Non-bloquant (silencieux si log-service down).  
**Vérifier :**
```bash
make start-docker
curl http://localhost:8000/health   # génère un log INFO

# Consulter les logs centralisés :
curl "http://localhost:5002/v1/logs?service=backend&limit=10"
# → {"total":N,"entries":[{"ts":"...","service":"backend","level":"INFO",...}]}

# Vérifier le fichier local :
cat tmp/logs/backend.log   # JSON une ligne par entrée
cat tmp/logs/all.log       # tous les services confondus
```

---

### US-14 · Docker Compose production-ready 🔄 en cours
**Objectif :** `restart: unless-stopped` sur tous les services, health checks, resource limits, `.env` pour tous les secrets, 0 mot de passe hardcodé.  
**Vérifier (une fois fait) :**
```bash
make start-docker
docker inspect docker_covid-backend-1 | grep -A5 RestartPolicy
# → "Name": "unless-stopped"
docker inspect docker_covid-backend-1 | grep -A10 Healthcheck
# → Test, Interval, Retries définis
grep -r "POSTGRES_PASSWORD" infrastructure/docker-compose.yml
# → doit afficher seulement "${POSTGRES_PASSWORD}" (pas de valeur en dur)
cat .env | grep POSTGRES_PASSWORD   # → valeur réelle dans .env (gitignored)
```

---

## Récap rapide

| US   | Titre                             | Statut |
|------|-----------------------------------|--------|
| US-01 | Repo Git unifié                  | ✅     |
| US-02 | API /health + /predict           | ✅     |
| US-03 | Docker Compose + GHCR            | ✅     |
| US-04 | Tests ≥ 40% coverage             | ✅     |
| US-05 | DVC + remote MinIO               | ✅     |
| US-06 | MLflow containerisé              | ✅     |
| US-07 | Architecture microservices       | ✅     |
| US-08 | DVC pipeline reproductible       | ✅     |
| US-09 | Qualité code                     | ✅     |
| US-10 | Refactoring scripts              | ✅     |
| US-11 | CI/CD complet deploy             | ⏳ (bloqué par US-14) |
| US-12 | Sécurité API                     | ⏳     |
| US-13 | Log-service centralisé           | ✅     |
| US-14 | Docker Compose prod-ready        | 🔄 en cours |
| US-15 | Load test P95 < 500ms            | ⏳     |
| US-16 | Data augmentation DVC            | ⏳     |
| US-17 | Dashboard agile                  | ✅     |
