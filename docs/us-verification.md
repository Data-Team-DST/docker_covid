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

> **Récap en direct** : `make verify` (ou `./verify.sh`) génère le vrai récapitulatif ✅/❌
> basé sur l'état actuel des services. Ce fichier documente le *quoi* et le *comment* ;
> `verify.sh` vérifie le *est-ce que ça marche*.
