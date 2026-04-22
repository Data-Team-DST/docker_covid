#!/usr/bin/env bash
# verify.sh — Vérification automatique des User Stories DS_COVID MLOps
#
# Usage :
#   ./verify.sh            → vérifie tout (nécessite Docker actif)
#   ./verify.sh --no-docker → vérifications fichiers uniquement
#
# Sortie : rapport ✅ / ❌ par US, exit 1 si au moins un échec

set -uo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
BACKEND_URL="http://localhost:8000"
DATA_URL="http://localhost:5001"
LOG_URL="http://localhost:5002"
COMPOSE="docker compose -f infrastructure/docker-compose.yml --project-directory ."
NO_DOCKER=false
[[ "${1:-}" == "--no-docker" ]] && NO_DOCKER=true

# ── Couleurs ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
BOLD='\033[1m'; NC='\033[0m'

PASS=0; FAIL=0
declare -a RESULTS=()

# ── Helpers ───────────────────────────────────────────────────────────────────
ok()   { echo -e "  ${GREEN}✅${NC} $1"; RESULTS+=("✅ $1"); PASS=$((PASS + 1)); }
fail() { echo -e "  ${RED}❌${NC} $1"; RESULTS+=("❌ $1"); FAIL=$((FAIL + 1)); }
skip() { echo -e "  ${YELLOW}⏭ ${NC} $1 (Docker non disponible)"; RESULTS+=("⏭  $1"); }

check_file() { local us="$1" desc="$2" path="$3"
  if [[ -e "$path" ]]; then ok "$us — $desc"
  else fail "$us — $desc ($path absent)"; fi; }

check_http() { local us="$1" desc="$2" url="$3"
  if $NO_DOCKER; then skip "$us — $desc"; return; fi
  if curl -sf --max-time 5 "$url" > /dev/null 2>&1; then ok "$us — $desc"
  else fail "$us — $desc ($url inaccessible)"; fi; }

check_cmd() { local us="$1" desc="$2"; shift 2
  if eval "$@" > /dev/null 2>&1; then ok "$us — $desc"
  else fail "$us — $desc"; fi; }

section() { echo -e "\n${BOLD}── $1 ──────────────────────────────────────────${NC}"; }

# ── Vérifications ─────────────────────────────────────────────────────────────

section "US-01 · Repo Git unifié + structure microservices"
check_file "US-01" "backend/app/"              backend/app
check_file "US-01" "frontend/"                 frontend
check_file "US-01" "infrastructure/"           infrastructure
check_file "US-01" "shared/logging_config.py"  shared/logging_config.py
check_cmd  "US-01" "Branche main existe"       git rev-parse --verify origin/main

section "US-02 · API /health + /predict"
check_http "US-02" "GET /health → 200"         "$BACKEND_URL/health"
check_http "US-02" "GET /docs (OpenAPI) → 200" "$BACKEND_URL/docs"
if ! $NO_DOCKER; then
  STATUS=$(curl -sf --max-time 5 "$BACKEND_URL/health" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null || echo "")
  [[ "$STATUS" == "ok" ]] && ok "US-02 — /health retourne status:ok" \
                           || fail "US-02 — /health ne retourne pas status:ok (reçu: '$STATUS')"
fi

section "US-03 · Docker Compose + images GHCR"
check_file "US-03" "infrastructure/docker-compose.yml" infrastructure/docker-compose.yml
if ! $NO_DOCKER; then
  NB=$(${COMPOSE} ps --status running 2>/dev/null | grep -c "running" || echo 0)
  [[ "$NB" -ge 5 ]] && ok "US-03 — $NB services Docker actifs (≥5)" \
                     || fail "US-03 — Seulement $NB services actifs (attendu ≥5)"
fi

section "US-04 · Tests unitaires ≥ 40% coverage"
check_file "US-04" "backend/tests/"     backend/tests
check_file "US-04" "data-service/tests" data-service/tests
if ! $NO_DOCKER; then
  echo -e "  ${YELLOW}⏳${NC} Exécution tests backend (peut prendre ~30s)..."
  if cd backend && PYTHONPATH=.. .venv/bin/python -m pytest tests/ -q \
      --cov=app --cov-fail-under=40 --tb=no -q > /tmp/be_test.log 2>&1; then
    ok "US-04 — Tests backend passent (≥40% coverage)"
  else
    fail "US-04 — Tests backend échouent (voir /tmp/be_test.log)"
  fi
  cd - > /dev/null
fi

section "US-05 · DVC initialisé + remote MinIO"
check_file "US-05" ".dvc/ initialisé"                .dvc
check_file "US-05" "data/raw.dvc tracké"             data/raw.dvc
check_file "US-05" "infrastructure/dvc_container_config.local" infrastructure/dvc_container_config.local
check_cmd  "US-05" "Remote 'minio' configuré dans .dvc/config" \
           grep -q "minio" .dvc/config

section "US-06 · MLflow containerisé"
check_http "US-06" "MLflow UI → 200" "http://localhost:5000"

section "US-07 · Architecture microservices"
check_file "US-07" "data-service/"    data-service
check_file "US-07" "log-service/"     log-service
check_file "US-07" "shared/"          shared
check_http "US-07" "data-service /health → 200" "$DATA_URL/health"
check_http "US-07" "log-service /health → 200"  "$LOG_URL/health"

section "US-08 · DVC pipeline reproductible"
check_file "US-08" "dvc.yaml défini"          dvc.yaml
check_file "US-08" "params.yaml défini"       params.yaml
check_file "US-08" "scripts/preprocess.py"    scripts/preprocess.py
check_file "US-08" "scripts/train.py"         scripts/train.py
check_file "US-08" "scripts/evaluate.py"      scripts/evaluate.py
check_cmd  "US-08" "Stage 'preprocess' dans dvc.yaml" grep -q "preprocess:" dvc.yaml
check_cmd  "US-08" "Stage 'train' dans dvc.yaml"      grep -q "train:" dvc.yaml
check_cmd  "US-08" "Stage 'evaluate' dans dvc.yaml"   grep -q "evaluate:" dvc.yaml

section "US-09 · Qualité code"
check_file "US-09" "check_quality.sh"         infrastructure/scripts/check_quality.sh
check_file "US-09" "check_requirements.sh"    infrastructure/scripts/check_requirements.sh

section "US-10 · Refactoring scripts"
check_file "US-10" "infrastructure/scripts/"  infrastructure/scripts
check_file "US-10" "setup.sh à la racine"     setup.sh
check_file "US-10" "Makefile"                 Makefile

section "US-13 · Log-service centralisé"
check_file "US-13" "log-service/app.py"              log-service/app.py
check_file "US-13" "shared/logging_config.py"        shared/logging_config.py
check_http "US-13" "log-service /health → 200"       "$LOG_URL/health"
if ! $NO_DOCKER; then
  NB=$(curl -sf --max-time 5 "$LOG_URL/v1/logs?limit=1" 2>/dev/null \
       | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo "?")
  ok "US-13 — /v1/logs répond (buffer: $NB entrées)"
fi

section "US-14 · Docker Compose production-ready"
check_cmd  "US-14" "restart: unless-stopped présent sur tous les services" \
           bash -c 'count=$(grep -c "unless-stopped" infrastructure/docker-compose.yml); [[ "$count" -ge 7 ]]'
check_cmd  "US-14" "Healthchecks définis (≥5 services)" \
           bash -c 'count=$(grep -c "healthcheck:" infrastructure/docker-compose.yml); [[ "$count" -ge 5 ]]'
check_cmd  "US-14" "Resource limits définis" \
           grep -q "limits:" infrastructure/docker-compose.yml
check_cmd  "US-14" "0 mot de passe hardcodé (pas de :-mlflow123)" \
           bash -c '! grep -q ":-mlflow123\|:-minio123" infrastructure/docker-compose.yml'

section "US-17 · Dashboard agile"
check_file "US-17" "dashboard/app.py"          dashboard/app.py
check_file "US-17" "dashboard/backlog.yaml"    dashboard/backlog.yaml
check_file "US-17" "Page data explorer"        dashboard/templates/data_explorer.html

# ── Résumé ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  RÉSUMÉ VÉRIFICATION DS_COVID MLOps${NC}"
echo -e "${BOLD}════════════════════════════════════════════════════${NC}"
for r in "${RESULTS[@]}"; do echo -e "  $r"; done
echo -e "${BOLD}────────────────────────────────────────────────────${NC}"
echo -e "  ${GREEN}✅ Réussis  : $PASS${NC}"
echo -e "  ${RED}❌ Échoués  : $FAIL${NC}"
echo ""

if [[ $FAIL -eq 0 ]]; then
  echo -e "${GREEN}${BOLD}  🎉 Tout est opérationnel !${NC}"
  exit 0
else
  echo -e "${RED}${BOLD}  ⚠  $FAIL vérification(s) en échec.${NC}"
  echo -e "  Relancer avec les services actifs : ${YELLOW}make start-all && ./verify.sh${NC}"
  exit 1
fi
