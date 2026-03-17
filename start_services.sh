#!/bin/bash
# start_services.sh — DS_COVID MLOps
# Lance les services Docker Compose et affiche les logs en temps réel
#
# Usage:
#   ./start_services.sh           → Phase 1 : backend uniquement
#   ./start_services.sh phase2    → Phase 2 : stack complète
#   ./start_services.sh stop      → Arrêt de tous les services
#   ./start_services.sh logs      → Logs en live (backend + frontend)

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

LOG_DIR="./tmp/logs"
mkdir -p "$LOG_DIR"

BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:8501"

MODE=${1:-phase1}

# =========================
# Fonctions utilitaires
# =========================
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}❌ Docker daemon non accessible${NC}"
        echo "   → Lance Docker Desktop ou : sudo systemctl start docker"
        exit 1
    fi
}

wait_for_service() {
    local name="$1"
    local url="$2"
    local max=30
    local attempt=1

    echo -e "${YELLOW}⏳ Attente ${name}...${NC}"
    while [ $attempt -le $max ]; do
        if curl -f -s --connect-timeout 3 "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ ${name} prêt${NC}"
            return 0
        fi
        sleep 2
        ((attempt++))
    done
    echo -e "${RED}❌ Timeout : ${name} non disponible après $((max * 2))s${NC}"
    return 1
}

show_urls() {
    echo ""
    echo -e "${BLUE}==============================${NC}"
    echo -e "${BLUE}  Services disponibles${NC}"
    echo -e "${BLUE}==============================${NC}"
    echo -e "  Backend API : ${GREEN}${BACKEND_URL}${NC}"
    echo -e "  Swagger     : ${GREEN}${BACKEND_URL}/docs${NC}"
    echo -e "  Health      : ${GREEN}${BACKEND_URL}/health${NC}"
    if [ "$MODE" != "phase1" ]; then
        echo -e "  Frontend    : ${GREEN}${FRONTEND_URL}${NC}"
        echo -e "  MLflow      : ${GREEN}http://localhost:5000${NC}"
        echo -e "  MinIO       : ${GREEN}http://localhost:9001${NC}"
    fi
    echo -e "${BLUE}==============================${NC}"
    echo ""
}

# =========================
# Commandes
# =========================
case "$MODE" in

    stop)
        echo -e "${YELLOW}Arrêt de tous les services...${NC}"
        docker compose down
        echo -e "${GREEN}✅ Services arrêtés${NC}"
        exit 0
        ;;

    logs)
        echo -e "${YELLOW}Logs en direct (Ctrl+C pour quitter)...${NC}"
        docker compose logs -f backend streamlit 2>/dev/null || \
        docker compose logs -f backend
        exit 0
        ;;

    phase2)
        check_docker
        echo -e "${GREEN}================================${NC}"
        echo -e "${GREEN}  DS_COVID — Phase 2 (full stack)${NC}"
        echo -e "${GREEN}================================${NC}"
        echo ""
        echo -e "${YELLOW}Build et démarrage de la stack complète...${NC}"
        docker compose up -d --build
        wait_for_service "Backend" "${BACKEND_URL}/health"
        show_urls
        ;;

    phase1|*)
        check_docker
        echo -e "${GREEN}==============================${NC}"
        echo -e "${GREEN}  DS_COVID — Phase 1 (backend)${NC}"
        echo -e "${GREEN}==============================${NC}"
        echo ""
        echo -e "${YELLOW}Build et démarrage du backend...${NC}"
        docker compose up -d --build backend
        wait_for_service "Backend" "${BACKEND_URL}/health"
        show_urls
        ;;

esac

# Logs en temps réel
echo -e "${YELLOW}Logs en direct (Ctrl+C pour quitter — services restent actifs)${NC}"
echo ""
trap 'echo -e "\n${YELLOW}Arrêt des logs (services toujours actifs)${NC}"; exit 0' SIGINT SIGTERM

docker compose logs -f backend 2>/dev/null &
LOG_PID=$!
wait $LOG_PID
