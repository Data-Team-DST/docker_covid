#!/usr/bin/env bash
# start_local.sh — DS_COVID MLOps
# Lance backend (FastAPI) + frontend (Streamlit) en local sans Docker
# Usage :
#   ./start_local.sh          → démarre les deux services
#   ./start_local.sh backend  → backend uniquement
#   ./start_local.sh frontend → frontend uniquement
#   ./start_local.sh stop     → arrête les services tournant sur 8000/8501

set -e

# ── Couleurs ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${SCRIPT_DIR}/backend"
FRONTEND_DIR="${SCRIPT_DIR}/frontend"
LOG_DIR="${SCRIPT_DIR}/tmp/logs"
VENV_DIR="${SCRIPT_DIR}/.venv"   # venv au ROOT (partage backend + frontend)

BACKEND_PORT=8000
FRONTEND_PORT=8501
BACKEND_URL="http://localhost:${BACKEND_PORT}"

MODE=${1:-both}

# ── Helpers ───────────────────────────────────────────────────────────────────
log()  { echo -e "${GREEN}[DS_COVID]${NC} $*"; }
warn() { echo -e "${YELLOW}[DS_COVID]${NC} $*"; }
err()  { echo -e "${RED}[DS_COVID]${NC} $*"; exit 1; }

mkdir -p "${LOG_DIR}"

# ── Stop ──────────────────────────────────────────────────────────────────────
if [ "$MODE" = "stop" ]; then
    warn "Arrêt des services sur les ports ${BACKEND_PORT} et ${FRONTEND_PORT}..."
    fuser -k ${BACKEND_PORT}/tcp 2>/dev/null && log "Backend arrêté" || warn "Rien sur :${BACKEND_PORT}"
    fuser -k ${FRONTEND_PORT}/tcp 2>/dev/null && log "Frontend arrêté" || warn "Rien sur :${FRONTEND_PORT}"
    exit 0
fi

# ── Verification venv root ────────────────────────────────────────────────────
check_venv() {
    if [ ! -d "${VENV_DIR}" ]; then
        err "Venv absent. Lance d abord : ./setup.sh"
    fi
    source "${VENV_DIR}/bin/activate"
    log "Venv active : ${VENV_DIR}"
}

# ── Lancer backend ────────────────────────────────────────────────────────────
start_backend() {
    log "Démarrage backend FastAPI (port ${BACKEND_PORT})..."
    check_venv

    PYTHONPATH="${BACKEND_DIR}" \
    nohup "${VENV_DIR}/bin/uvicorn" app.main:app \
        --host 0.0.0.0 \
        --port ${BACKEND_PORT} \
        --reload \
        --app-dir "${BACKEND_DIR}" \
        > "${LOG_DIR}/backend.log" 2>&1 &

    BACKEND_PID=$!
    echo $BACKEND_PID > "${LOG_DIR}/backend.pid"
    log "Backend lancé (PID: ${BACKEND_PID})"

    # Attendre que le backend soit prêt
    warn "Attente backend..."
    local attempt=0
    while [ $attempt -lt 20 ]; do
        if curl -s --connect-timeout 2 "${BACKEND_URL}/health" > /dev/null 2>&1; then
            log "Backend prêt : ${BACKEND_URL}"
            log "  Swagger   : ${BACKEND_URL}/docs"
            log "  Health    : ${BACKEND_URL}/health"
            return 0
        fi
        sleep 1
        ((attempt++))
    done
    err "Timeout : backend non joignable après 20s"
    err "Logs : ${LOG_DIR}/backend.log"
    tail -20 "${LOG_DIR}/backend.log"
    exit 1
}

# ── Lancer frontend ───────────────────────────────────────────────────────────
start_frontend() {
    log "Démarrage frontend Streamlit (port ${FRONTEND_PORT})..."
    check_venv

    BACKEND_URL="http://localhost:${BACKEND_PORT}" \
    nohup "${VENV_DIR}/bin/streamlit" run "${FRONTEND_DIR}/streamlit_app.py" \
        --server.port ${FRONTEND_PORT} \
        --server.address 0.0.0.0 \
        --server.headless true \
        > "${LOG_DIR}/frontend.log" 2>&1 &

    FRONTEND_PID=$!
    echo $FRONTEND_PID > "${LOG_DIR}/frontend.pid"
    log "Frontend lancé (PID: ${FRONTEND_PID})"
    sleep 2
    log "Frontend : http://localhost:${FRONTEND_PORT}"
}

# ── Affichage final + logs live ───────────────────────────────────────────────
show_status() {
    echo ""
    echo -e "${BLUE}=================================${NC}"
    echo -e "${BLUE}  DS_COVID — Services actifs${NC}"
    echo -e "${BLUE}=================================${NC}"
    echo -e "  Backend  : ${GREEN}http://localhost:${BACKEND_PORT}${NC}"
    echo -e "  Swagger  : ${GREEN}http://localhost:${BACKEND_PORT}/docs${NC}"
    echo -e "  Frontend : ${GREEN}http://localhost:${FRONTEND_PORT}${NC}"
    echo -e "  Logs BE  : ${LOG_DIR}/backend.log"
    echo -e "  Logs FE  : ${LOG_DIR}/frontend.log"
    echo -e "${BLUE}=================================${NC}"
    echo ""
    echo -e "${YELLOW}Ctrl+C pour quitter les logs (services restent actifs)${NC}"
    echo -e "${YELLOW}./start_local.sh stop  → arrêter les services${NC}"
    echo ""
}

cleanup() {
    echo ""
    warn "Arrêt des logs (services toujours actifs en arrière-plan)"
    exit 0
}
trap cleanup SIGINT SIGTERM

# ── Main ──────────────────────────────────────────────────────────────────────
echo ""
log "================================="
log "  DS_COVID — Lancement local"
log "================================="
echo ""

case "$MODE" in
    backend)
        start_backend
        show_status
        tail -f "${LOG_DIR}/backend.log"
        ;;
    frontend)
        start_frontend
        show_status
        tail -f "${LOG_DIR}/frontend.log"
        ;;
    both|*)
        start_backend
        start_frontend
        show_status
        tail -f "${LOG_DIR}/backend.log" "${LOG_DIR}/frontend.log"
        ;;
esac
