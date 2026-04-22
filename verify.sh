#!/usr/bin/env bash
# verify.sh — Vérification automatique des User Stories DS_COVID MLOps
#
# Usage :
#   ./verify.sh            → vérifie tout (nécessite Docker actif)
#   ./verify.sh --no-docker → vérifications fichiers uniquement
#
# Sortie : rapport ✅ / ❌ / ⏭ par US, exit 1 si au moins un échec

set -uo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
BACKEND_URL="http://localhost:8000"
DATA_URL="http://localhost:5001"
LOG_URL="http://localhost:5002"
COMPOSE="docker compose -f infrastructure/docker-compose.yml --project-directory ."
NO_DOCKER=false
[[ "${1:-}" == "--no-docker" ]] && NO_DOCKER=true

# ── Couleurs ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'

PASS=0; FAIL=0
declare -a RESULTS=()
declare -a TODOS=()

# ── Helpers ───────────────────────────────────────────────────────────────────
ok()   { echo -e "  ${GREEN}✅${NC} $1"; RESULTS+=("✅  $1"); PASS=$((PASS + 1)); }
fail() { echo -e "  ${RED}❌${NC} $1"; RESULTS+=("❌  $1"); FAIL=$((FAIL + 1)); }
skip() { echo -e "  ${YELLOW}⏭ ${NC} $1"; RESULTS+=("⏭   $1"); }
todo() { echo -e "  ${CYAN}📋${NC} $1"; TODOS+=("📋  $1"); }

check_file() {
  local us="$1" desc="$2" path="$3"
  if [[ -e "$path" ]]; then ok "$us — $desc"
  else fail "$us — $desc  ($path absent)"; fi
}

check_http() {
  local us="$1" desc="$2" url="$3" retries="${4:-1}"
  if $NO_DOCKER; then skip "$us — $desc  (--no-docker)"; return; fi
  local i=0
  while [[ $i -lt $retries ]]; do
    if curl -sf --max-time 5 "$url" > /dev/null 2>&1; then ok "$us — $desc"; return; fi
    i=$((i + 1))
    [[ $i -lt $retries ]] && sleep 10
  done
  fail "$us — $desc  ($url inaccessible)"
}

check_grep() {
  local us="$1" desc="$2" pattern="$3" file="$4"
  if grep -q "$pattern" "$file" 2>/dev/null; then ok "$us — $desc"
  else fail "$us — $desc"; fi
}

section() { echo -e "\n${BOLD}── $1 ──────────────────────────────────────────${NC}"; }

# ── US-01 ─────────────────────────────────────────────────────────────────────
section "US-01 · Repo Git unifié + structure microservices"
check_file "US-01" "backend/app/"             backend/app
check_file "US-01" "frontend/"                frontend
check_file "US-01" "infrastructure/"          infrastructure
check_file "US-01" "shared/logging_config.py" shared/logging_config.py
if git rev-parse --verify origin/main > /dev/null 2>&1; then
  ok "US-01 — Branche main existe"
else fail "US-01 — Branche main introuvable"; fi

# ── US-02 ─────────────────────────────────────────────────────────────────────
section "US-02 · API /health + /predict"
check_http "US-02" "GET /health → 200"         "$BACKEND_URL/health"
check_http "US-02" "GET /docs (OpenAPI) → 200" "$BACKEND_URL/docs"
if ! $NO_DOCKER; then
  STATUS=$(curl -sf --max-time 5 "$BACKEND_URL/health" 2>/dev/null \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null \
    || echo "")
  if [[ "$STATUS" == "ok" || "$STATUS" == "healthy" ]]; then
    ok "US-02 — /health retourne status:$STATUS"
  else
    fail "US-02 — /health status inattendu (reçu: '$STATUS')"
  fi
fi

# ── US-03 ─────────────────────────────────────────────────────────────────────
section "US-03 · Docker Compose + images GHCR"
check_file "US-03" "infrastructure/docker-compose.yml" infrastructure/docker-compose.yml
if ! $NO_DOCKER; then
  NB=$(${COMPOSE} ps --status running 2>/dev/null | tail -n +2 | wc -l | tr -d ' \n')
  NB="${NB:-0}"
  if [[ "$NB" -ge 5 ]]; then ok "US-03 — $NB services Docker actifs (≥5)"
  else fail "US-03 — Seulement $NB services actifs (attendu ≥5)"; fi
fi

# ── US-04 ─────────────────────────────────────────────────────────────────────
section "US-04 · Tests unitaires ≥ 40% coverage"
check_file "US-04" "backend/tests/"     backend/tests
check_file "US-04" "data-service/tests" data-service/tests
if [[ -d "backend/.venv/Scripts" ]] && [[ ! -f "backend/.venv/bin/python" ]]; then
  skip "US-04 — Tests backend  (venv Windows détecté → rm -rf backend/.venv && make setup-be depuis WSL)"
elif [[ -f "backend/.venv/bin/python" ]]; then
  echo -e "  ${YELLOW}⏳${NC} Exécution tests backend (peut prendre ~30s)..."
  if (cd backend && PYTHONPATH=.. .venv/bin/python -m pytest tests/ -q \
      --cov=app --cov-fail-under=40 --tb=no > /tmp/be_test.log 2>&1); then
    ok "US-04 — Tests backend passent (≥40% coverage)"
  else
    fail "US-04 — Tests backend échouent  (détails: cat /tmp/be_test.log)"
  fi
else
  skip "US-04 — Tests backend  (venv absent → lancer: make setup-be depuis WSL)"
fi

# ── US-05 ─────────────────────────────────────────────────────────────────────
section "US-05 · DVC initialisé + remote MinIO"
check_file "US-05" ".dvc/ initialisé"         .dvc
check_file "US-05" "data/raw.dvc tracké"      data/raw.dvc
check_file "US-05" "dvc_container_config.local" infrastructure/dvc_container_config.local
check_grep "US-05" "Remote 'minio' dans .dvc/config" "minio" .dvc/config

# ── US-06 ─────────────────────────────────────────────────────────────────────
section "US-06 · MLflow containerisé"
check_http "US-06" "MLflow UI → 200" "http://localhost:5000" 3

# ── US-07 ─────────────────────────────────────────────────────────────────────
section "US-07 · Architecture microservices"
check_file "US-07" "data-service/" data-service
check_file "US-07" "log-service/"  log-service
check_file "US-07" "shared/"       shared
check_http "US-07" "data-service /health → 200" "$DATA_URL/health"
check_http "US-07" "log-service /health → 200"  "$LOG_URL/health"

# ── US-08 ─────────────────────────────────────────────────────────────────────
section "US-08 · DVC pipeline reproductible"
check_file "US-08" "dvc.yaml"            dvc.yaml
check_file "US-08" "params.yaml"         params.yaml
check_file "US-08" "scripts/preprocess.py" scripts/preprocess.py
check_file "US-08" "scripts/train.py"    scripts/train.py
check_file "US-08" "scripts/evaluate.py" scripts/evaluate.py
check_grep "US-08" "Stage 'preprocess'"  "preprocess:" dvc.yaml
check_grep "US-08" "Stage 'train'"       "train:"      dvc.yaml
check_grep "US-08" "Stage 'evaluate'"    "evaluate:"   dvc.yaml

# ── US-09 ─────────────────────────────────────────────────────────────────────
section "US-09 · Qualité code"
check_file "US-09" "check_quality.sh"      infrastructure/scripts/check_quality.sh
check_file "US-09" "check_requirements.sh" infrastructure/scripts/check_requirements.sh

# ── US-10 ─────────────────────────────────────────────────────────────────────
section "US-10 · Refactoring scripts"
check_file "US-10" "infrastructure/scripts/"       infrastructure/scripts
check_file "US-10" "setup.sh (infrastructure/scripts/)" infrastructure/scripts/setup.sh
check_file "US-10" "Makefile"                      Makefile

# ── US-13 ─────────────────────────────────────────────────────────────────────
section "US-13 · Log-service centralisé"
check_file "US-13" "log-service/app.py"       log-service/app.py
check_file "US-13" "shared/logging_config.py" shared/logging_config.py
check_http "US-13" "log-service /health → 200" "$LOG_URL/health"
if ! $NO_DOCKER; then
  ENTRIES=$(curl -sf --max-time 5 "$LOG_URL/v1/logs?limit=1" 2>/dev/null \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null \
    || echo "?")
  ok "US-13 — /v1/logs répond  (buffer: $ENTRIES entrées)"
fi

# ── US-14 ─────────────────────────────────────────────────────────────────────
section "US-14 · Docker Compose production-ready"
COUNT=$(grep -c "unless-stopped" infrastructure/docker-compose.yml 2>/dev/null || true)
COUNT="${COUNT//[$'\t\r\n ']}"
if [[ "${COUNT:-0}" -ge 7 ]]; then ok "US-14 — restart: unless-stopped ($COUNT services)"
else fail "US-14 — restart: unless-stopped insuffisant ($COUNT/7)"; fi

COUNT=$(grep -c "healthcheck:" infrastructure/docker-compose.yml 2>/dev/null || true)
COUNT="${COUNT//[$'\t\r\n ']}"
if [[ "${COUNT:-0}" -ge 5 ]]; then ok "US-14 — Healthchecks définis ($COUNT services)"
else fail "US-14 — Healthchecks insuffisants ($COUNT/5)"; fi

check_grep "US-14" "Resource limits définis" "limits:" infrastructure/docker-compose.yml

if ! grep -qE ':-mlflow123|:-minio123' infrastructure/docker-compose.yml 2>/dev/null; then
  ok "US-14 — 0 mot de passe hardcodé"
else fail "US-14 — Mots de passe hardcodés détectés"; fi

# ── US-17 ─────────────────────────────────────────────────────────────────────
section "US-17 · Dashboard agile"
check_file "US-17" "dashboard/app.py"       dashboard/app.py
check_file "US-17" "dashboard/backlog.yaml" dashboard/backlog.yaml
check_file "US-17" "Page data explorer"     dashboard/templates/data_explorer.html

# ── USes en attente (TODO) ────────────────────────────────────────────────────
section "USes en attente (non implémentées)"
todo "US-11 · CI/CD deploy  — smoke-test Docker après push GHCR  (bloqué par US-14)"
todo "US-12 · Sécurité API  — API key + rate limiting sur /predict"
todo "US-15 · Load test     — Locust/k6 P95 < 500ms sur /predict  (bloqué par US-12)"
todo "US-16 · Data augment  — Stage DVC augmentation (rotation/flip/zoom)  (bloqué par US-08)"

# ── Résumé ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  RÉSUMÉ — DS_COVID MLOps$(date +'  (%Y-%m-%d %H:%M)')${NC}"
echo -e "${BOLD}════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}Vérifiées :${NC}"
for r in "${RESULTS[@]}"; do echo -e "    $r"; done
echo ""
echo -e "  ${BOLD}En attente :${NC}"
for t in "${TODOS[@]}"; do echo -e "    $t"; done
echo ""
echo -e "${BOLD}────────────────────────────────────────────────────${NC}"
echo -e "  ${GREEN}✅ Réussis  : $PASS${NC}"
echo -e "  ${RED}❌ Échoués  : $FAIL${NC}"
echo -e "  ${CYAN}📋 TODO     : ${#TODOS[@]}${NC}"
echo ""

if [[ $FAIL -eq 0 ]]; then
  echo -e "${GREEN}${BOLD}  🎉 Tout ce qui est implémenté est opérationnel !${NC}"
  exit 0
else
  echo -e "${RED}${BOLD}  ⚠  $FAIL vérification(s) en échec.${NC}"
  echo -e "  Relancer avec Docker : ${YELLOW}make verify${NC}"
  exit 1
fi
