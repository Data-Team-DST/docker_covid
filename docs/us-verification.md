# Vérification des User Stories — DS_COVID MLOps

Pour chaque US terminée : ce qui a été fait + comment vérifier sans ambiguïté.

> **Windows / PowerShell** : `curl` est un alias de `Invoke-WebRequest` en PowerShell.
> Utiliser soit `curl.exe` (disponible depuis Win10), soit lancer les commandes depuis WSL (`wsl bash`).
> Les exemples ci-dessous utilisent la syntaxe **bash / WSL**.

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
# WSL / Linux / macOS  (lancer depuis la racine du repo docker_covid)
make start-docker          # ou ./start_local.sh
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/v1/predict \
     -F "file=@data/raw/COVID-19_Radiography_Dataset/COVID/images/COVID-1.png"
# → {"class":"COVID","confidence":0.97,"scores":{...}}
```
```powershell
# PowerShell (Windows)  (lancer depuis la racine du repo docker_covid)
curl.exe http://localhost:8000/health
curl.exe -X POST http://localhost:8000/api/v1/predict -F "file=@data/raw/COVID-19_Radiography_Dataset/COVID/images/COVID-1.png"
```

---

### US-03 · Docker Compose + images GHCR ✅
**Fait :** `infrastructure/docker-compose.yml` (7 services). Images publiées sur GHCR via CI. Tags `sha-*`, branche, `latest` sur main.  
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

### US-14 · Docker Compose production-ready ✅
**Fait (Steven) :** `restart: unless-stopped` sur 8 services, healthchecks sur 7 services, `deploy.resources.limits` sur tous, 0 secret hardcodé — toutes les variables dans `.env`. MLflow containerisé avec `start.sh` (db upgrade automatique au démarrage).  
**Vérifier :**
```bash
make start-docker
docker inspect covid-xray-backend | grep -A5 RestartPolicy
# → "Name": "unless-stopped"
docker inspect covid-xray-backend | grep -A10 Healthcheck
# → Test, Interval, Retries définis
grep "POSTGRES_PASSWORD" infrastructure/docker-compose.yml
# → affiche uniquement "${POSTGRES_PASSWORD}" — jamais de valeur en dur
make verify   # → 46 ✅, 0 ❌
```

---

## S3 (suite) — US en attente

### US-11 · CI/CD pipeline complet 🔄 en cours
**Objectif :** lint → test → SonarCloud → build/push GHCR → **smoke-test deploy** (docker run + curl /health). CI < 10 min, 100% vert sur main.  
**Ce qui existe déjà :** Lint BE/DS/FE + Test BE/DS/FE + SonarCloud + Build BE/FE/DS — tous ✅ dans `cicd.yml`  
**Ce qui manque :** job `deploy` — pull l'image depuis GHCR, `docker run`, `curl /health`, stop. Tourne dans le runner GitHub Actions (gratuit, zéro VPS).  
**Vérifier (une fois fait) :**
```bash
# GitHub Actions → cicd.yml → job "Deploy smoke-test"
# → "GET /health → 200 ✅" dans les logs du runner
```

---

### US-12 · Sécurité API 🔄 à faire
**Objectif :** API key obligatoire sur tous les endpoints (401 si absent), rate limiting (100 req/min), validation Pydantic stricte sur `/predict`.  
**Vérifier (une fois fait) :**
```bash
curl http://localhost:8000/health                          # → 401 Unauthorized
curl -H "X-API-Key: secret" http://localhost:8000/health  # → 200
```

---

### US-15 · Load test P95 < 500ms 🔄 bloqué par US-12
**Objectif :** Script locust/k6, 10 req/s sur `/predict`, P95 < 500ms, rapport HTML dans `outputs/load_test/`.  
**Vérifier (une fois fait) :**
```bash
make load-test   # → outputs/load_test/report.html, P95 < 500ms
```

---

### US-16 · Data augmentation DVC 🔄 bloqué par US-08
**Objectif :** Stage `augment` dans `dvc.yaml` (rotation, flip, zoom, brightness). 42 330 → ~170 000 images.  
**Vérifier (une fois fait) :**
```bash
dvc repro        # → stage augment s'exécute avant preprocess
ls data/augmented/
```

---

## S4 — Monitoring, Drift & Maintenance

### US-18 · Prometheus + instrumentation FastAPI 🔄 à faire
**Objectif :** `prometheus-fastapi-instrumentator` sur `/predict` et `/health`. Métriques : latence P50/P95, throughput, error rate, confidence distribution. Endpoint `/metrics`.  
**Vérifier (une fois fait) :**
```bash
make start-docker
curl http://localhost:8000/metrics   # → format Prometheus (# HELP, # TYPE, ...)
```

---

### US-19 · Grafana dashboard ≥ 5 panels + alertes 🔄 à faire
**Objectif :** Dashboard Grafana provisionné via docker-compose. Panels : latence P50/P95, error rate, throughput, confidence moyenne, distribution classes. Alertes si P95 > 1s ou error rate > 5%.  
**Vérifier (une fois fait) :**
```bash
make start-docker
open http://localhost:3000   # → dashboard "DS_COVID" avec ≥5 panels
```

---

### US-20 · Evidently — détection dérive données 🔄 à faire
**Objectif :** Rapport Evidently (PSI + Jensen-Shannon) comparant distribution production vs train. Alerte si PSI > 0.2.  
**Vérifier (une fois fait) :**
```bash
python scripts/drift_report.py   # → outputs/drift/report.html
open outputs/drift/report.html   # → tableau PSI par feature, seuil 0.2 coloré
```

---

### US-21 · Pipeline re-entraînement semi-automatique 🔄 à faire
**Objectif :** `trigger_retrain.sh` : détecte dérive (PSI > 0.2) → lance training DVC → log MLflow → promeut si accuracy ≥ 85% (confirmation manuelle).  
**Vérifier (une fois fait) :**
```bash
bash scripts/trigger_retrain.sh --dry-run   # → affiche ce qui serait fait
```

---

### US-22 · Documentation finale — README + ADRs + runbooks 🔄 à faire
**Objectif :** README : clone → services up en 3 commandes. ADRs dans `docs/adr/`. Runbooks dans `docs/runbooks/` (restart, rollback modèle, re-entraînement).  
**Vérifier (une fois fait) :**
```bash
# Peer review : clone depuis zéro, suivre le README
git clone https://github.com/Data-Team-DST/docker_covid.git && cd docker_covid
make setup && make start-all   # → tous les services up sans intervention manuelle
ls docs/adr/ docs/runbooks/
```

---

> **Récap en direct** : `make verify` (ou `./verify.sh`) génère le vrai récapitulatif ✅/❌
> basé sur l'état actuel des services. Ce fichier documente le *quoi* et le *comment* ;
> `verify.sh` vérifie le *est-ce que ça marche*.
