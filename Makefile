# DS_COVID MLOps — Makefile
# Environnement reproductible en une commande
#
# Prérequis : Docker Desktop lancé (ou Docker sur WSL2)
#
# Usage rapide :
#   make setup      → première installation (cp .env, mkdir data...)
#   make start      → démarre le backend (Phase 1)
#   make start-all  → démarre la stack complète (Phase 2)
#   make stop       → arrête tous les containers
#   make test       → lance les tests unitaires
#   make lint       → vérifie la qualité du code
#   make fix        → auto-corrige le style (black/ruff/isort)
#   make logs       → affiche les logs en direct
#   make clean      → nettoie __pycache__, .coverage, tmp/

.PHONY: all setup setup-check start start-local start-docker start-all \
        stop restart logs test lint fix clean build shell help \
        dvc-setup dvc-push dvc-pull

# ── Couleurs ──────────────────────────────────────────────────────────────────
GREEN  := \033[0;32m
YELLOW := \033[1;33m
RED    := \033[0;31m
NC     := \033[0m

# ── Variables ─────────────────────────────────────────────────────────────────
BACKEND_URL  := http://localhost:8000
FRONTEND_URL := http://localhost:8501
PYTHON       := python3

# ── Défaut ────────────────────────────────────────────────────────────────────
all: help

# ── Setup ─────────────────────────────────────────────────────────────────────
setup: ## Setup complet : venv, deps, .env, dossiers (run once apres git clone)
	@bash setup.sh

setup-check: ## Verifie l etat de l environnement local
	@bash setup.sh --check

# ── Local (sans Docker) ──────────────────────────────────────────────────────
start-local: ## Lance backend + frontend en local (necessite setup)
	@bash start_local.sh

# ── Docker ────────────────────────────────────────────────────────────────────
start-docker: ## Lance le backend via Docker (zero Python requis)
	@bash start_services.sh phase1

start: ## Lance le backend FastAPI (Phase 1) via Docker
	@echo "$(YELLOW)Démarrage backend DS_COVID...$(NC)"
	docker compose down 2>/dev/null || true
	docker compose up -d --build backend
	@echo "$(GREEN)✅ Backend disponible :$(NC)"
	@echo "   API    : $(BACKEND_URL)"
	@echo "   Swagger: $(BACKEND_URL)/docs"
	@echo "   Health : $(BACKEND_URL)/health"

start-all: ## Lance la stack complète : backend + frontend + mlflow + minio + postgres
	@echo "$(YELLOW)Démarrage stack complète DS_COVID (Phase 2)...$(NC)"
	docker compose down 2>/dev/null || true
	docker compose up -d --build
	@echo "$(GREEN)✅ Services disponibles :$(NC)"
	@echo "   Backend  : $(BACKEND_URL)"
	@echo "   Frontend : $(FRONTEND_URL)"
	@echo "   MLflow   : http://localhost:5000"
	@echo "   MinIO    : http://localhost:9001"

stop: ## Arrête tous les containers
	@echo "$(YELLOW)Arrêt des services...$(NC)"
	docker compose down
	@echo "$(GREEN)✅ Services arrêtés$(NC)"

restart: stop start ## Redémarre le backend

build: ## Build les images sans lancer
	docker compose build backend

logs: ## Affiche les logs en direct
	docker compose logs -f backend

logs-all: ## Affiche les logs de tous les services
	docker compose logs -f

shell: ## Ouvre un shell dans le container backend
	docker compose exec backend bash

status: ## Status des containers
	docker compose ps

# ── DVC ───────────────────────────────────────────────────────────────────────
dvc-setup: ## Configure DVC remote MinIO (credentials locaux, gitignorés)
	@echo "$(YELLOW)Configuration DVC remote MinIO...$(NC)"
	@echo "[remote \"minio\"]" > .dvc/config.local
	@echo "    access_key_id = minioadmin" >> .dvc/config.local
	@echo "    secret_access_key = minioadmin" >> .dvc/config.local
	@echo "$(GREEN)✅ .dvc/config.local créé$(NC)"

dvc-push: ## Pousse les données vers MinIO (make start-all requis)
	@echo "$(YELLOW)Push DVC → MinIO...$(NC)"
	@.venv/bin/dvc push || dvc push
	@echo "$(GREEN)✅ Données pushées$(NC)"

dvc-pull: ## Récupère les données depuis MinIO
	@echo "$(YELLOW)Pull DVC ← MinIO...$(NC)"
	@.venv/bin/dvc pull || dvc pull
	@echo "$(GREEN)✅ Données récupérées$(NC)"

# ── Tests ─────────────────────────────────────────────────────────────────────
test: ## Lance les tests unitaires (local, sans Docker)
	@echo "$(YELLOW)Tests unitaires backend...$(NC)"
	cd backend && $(PYTHON) -m pytest tests/ -v \
		--cov=app \
		--cov-report=term-missing \
		--cov-report=xml:coverage.xml \
		--cov-fail-under=40
	@echo "$(GREEN)✅ Tests OK$(NC)"

test-docker: ## Lance les tests dans le container Docker
	docker compose exec backend pytest tests/ -v --cov=app

# ── Qualité ───────────────────────────────────────────────────────────────────
lint: ## Vérifie la qualité du code (ruff + pylint + structure)
	@echo "$(YELLOW)Vérification qualité...$(NC)"
	@./check_quality.sh --skip-pylint

lint-full: ## Vérification qualité complète (avec pylint)
	@./check_quality.sh

fix: ## Auto-corrige le style (black + isort + ruff)
	@./fix_style.sh

smell: ## Analyse code smell uniquement
	@$(PYTHON) -c "\
import sys; sys.path.insert(0, '.'); \
exec(open('check_code_smell_parser.py').read()); \
from pathlib import Path; \
[print(evaluate_file(f, sum(1 for _ in open(f)), 100)['message'], f) \
 for f in sorted(Path('backend/app').rglob('*.py')) \
 if '__pycache__' not in str(f)]"

# ── Nettoyage ─────────────────────────────────────────────────────────────────
clean: ## Nettoie __pycache__, .coverage, tmp/quality
	@echo "$(YELLOW)Nettoyage...$(NC)"
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete 2>/dev/null || true
	find . -name '.coverage' -delete 2>/dev/null || true
	rm -f backend/coverage.xml
	rm -rf tmp/quality/
	mkdir -p tmp/quality
	@echo "$(GREEN)✅ Nettoyage terminé$(NC)"

clean-docker: ## Supprime les images et volumes Docker du projet
	docker compose down -v --rmi local 2>/dev/null || true

# ── Help ──────────────────────────────────────────────────────────────────────
help: ## Affiche cette aide
	@echo ""
	@echo "$(GREEN)DS_COVID MLOps — Commandes disponibles$(NC)"
	@echo "======================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Démarrage rapide :$(NC)"
	@echo "  make setup && make start"
	@echo ""
