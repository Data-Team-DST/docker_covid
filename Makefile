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

.PHONY: all setup setup-check setup-be setup-ds start start-local start-docker start-all \
        stop restart logs logs-all test test-be test-ds verify lint fix clean build shell help dashboard \
        data-build data-start data-stop data-logs data-test data-shell \
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
SCRIPTS      := infrastructure/scripts
COMPOSE      := docker compose -f infrastructure/docker-compose.yml --project-directory .

# ── Défaut ────────────────────────────────────────────────────────────────────
all: help

# ── Setup ─────────────────────────────────────────────────────────────────────
setup: ## Setup complet : venv, deps, .env, dossiers (run once apres git clone)
	@bash $(SCRIPTS)/setup.sh

setup-check: ## Verifie l etat de l environnement local
	@bash $(SCRIPTS)/setup.sh --check

# ── Local (sans Docker) ──────────────────────────────────────────────────────
start-local: ## Lance backend + frontend en local (necessite setup)
	@bash $(SCRIPTS)/start_local.sh

# ── Docker ────────────────────────────────────────────────────────────────────
start-docker: ## Lance le backend via Docker (zero Python requis)
	@bash $(SCRIPTS)/start_services.sh phase1

start: ## Lance le backend FastAPI (Phase 1) via Docker
	@echo "$(YELLOW)Démarrage backend DS_COVID...$(NC)"
	$(COMPOSE) down 2>/dev/null || true
	$(COMPOSE) up -d --build backend
	@echo "$(GREEN)✅ Backend disponible :$(NC)"
	@echo "   API    : $(BACKEND_URL)"
	@echo "   Swagger: $(BACKEND_URL)/docs"
	@echo "   Health : $(BACKEND_URL)/health"

start-all: ## Lance la stack complète : backend + frontend + mlflow + minio + postgres
	@echo "$(YELLOW)Démarrage stack complète DS_COVID (Phase 2)...$(NC)"
	$(COMPOSE) down 2>/dev/null || true
	$(COMPOSE) up -d --build
	@echo "$(GREEN)✅ Services disponibles :$(NC)"
	@echo "   Backend  : $(BACKEND_URL)"
	@echo "   Frontend : $(FRONTEND_URL)"
	@echo "   MLflow   : http://localhost:5000"
	@echo "   MinIO    : http://localhost:9001"

stop: ## Arrête tous les containers
	@echo "$(YELLOW)Arrêt des services...$(NC)"
	$(COMPOSE) down
	@echo "$(GREEN)✅ Services arrêtés$(NC)"

restart: stop start ## Redémarre le backend

build: ## Build les images sans lancer
	$(COMPOSE) build backend

logs: ## Affiche les logs en direct (Ctrl+C arrête les services)
	@trap '$(COMPOSE) down 2>/dev/null; echo "$(GREEN)Services arrêtés$(NC)"; exit 0' INT; \
	 $(COMPOSE) logs -f backend

logs-all: ## Affiche les logs de tous les services (Ctrl+C arrête les services)
	@trap '$(COMPOSE) down 2>/dev/null; echo "$(GREEN)Services arrêtés$(NC)"; exit 0' INT; \
	 $(COMPOSE) logs -f

shell: ## Ouvre un shell dans le container backend
	$(COMPOSE) exec backend bash

status: ## Status des containers
	$(COMPOSE) ps

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

# ── Venvs par service ─────────────────────────────────────────────────────────
setup-be: ## Crée/met à jour le venv backend (backend/.venv, sans tensorflow)
	@if [ -d backend/.venv/Scripts ] && [ ! -f backend/.venv/bin/python ]; then \
		echo "$(RED)⚠ venv Windows détecté — suppression et recréation depuis WSL$(NC)"; \
		rm -rf backend/.venv; \
	fi
	@if [ ! -f backend/.venv/bin/python ]; then \
		echo "$(YELLOW)Création venv backend...$(NC)"; \
		$(PYTHON) -m venv backend/.venv; \
	fi
	@echo "$(YELLOW)Installation deps backend...$(NC)"
	@backend/.venv/bin/pip install -q -r backend/requirements-dev.txt
	@echo "$(GREEN)✅ backend/.venv prêt$(NC)"

setup-ds: ## Crée/met à jour le venv data-service (data-service/.venv)
	@if [ ! -f data-service/.venv/bin/python ]; then \
		echo "$(YELLOW)Création venv data-service...$(NC)"; \
		$(PYTHON) -m venv data-service/.venv; \
	fi
	@echo "$(YELLOW)Installation deps data-service...$(NC)"
	@data-service/.venv/bin/pip install -q \
		-r data-service/requirements.txt \
		-r data-service/dev-requirements.txt
	@echo "$(GREEN)✅ data-service/.venv prêt$(NC)"

# ── Tests ─────────────────────────────────────────────────────────────────────
test: test-be test-ds ## Lance les tests de tous les microservices (venvs isolés)

test-be: setup-be ## Tests backend dans son venv isolé
	@echo "$(YELLOW)── Tests backend ──────────────────────────────────────$(NC)"
	@cd backend && PYTHONPATH=.. .venv/bin/python -m pytest tests/ -v \
		--cov=app \
		--cov-report=term-missing \
		--cov-report=xml:coverage.xml \
		--cov-fail-under=40
	@echo "$(GREEN)✅ Tests backend OK$(NC)"

test-ds: setup-ds ## Tests data-service dans son venv isolé
	@echo "$(YELLOW)── Tests data-service ─────────────────────────────────$(NC)"
	@cd data-service && PYTHONPATH=src:.. .venv/bin/python -m pytest tests/ -v \
		--cov=data_service \
		--cov-report=term-missing \
		--cov-report=xml:ds-coverage.xml \
		--cov-fail-under=30
	@echo "$(GREEN)✅ Tests data-service OK$(NC)"

test-docker: ## Lance les tests dans le container Docker
	docker compose exec backend pytest tests/ -v --cov=app

verify: ## Lance start-all puis vérifie toutes les US (démo tuteur)
	@echo "$(YELLOW)Démarrage de la stack...$(NC)"
	@$(COMPOSE) up -d --build 2>/dev/null || true
	@echo "$(YELLOW)Attente que les services soient healthy (60s)...$(NC)"
	@sleep 60
	@bash verify.sh

# ── Qualité ───────────────────────────────────────────────────────────────────
lint: ## Vérifie la qualité du code (ruff + pylint + structure)
	@echo "$(YELLOW)Vérification qualité...$(NC)"
	@bash $(SCRIPTS)/check_quality.sh --skip-pylint

lint-full: ## Vérification qualité complète (avec pylint)
	@bash $(SCRIPTS)/check_quality.sh

fix: ## Auto-corrige le style (black + isort + ruff)
	@bash $(SCRIPTS)/fix_style.sh

smell: ## Analyse code smell uniquement
	@$(PYTHON) -c "\
import sys; sys.path.insert(0, '.'); \
exec(open('$(SCRIPTS)/check_code_smell_parser.py').read()); \
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

# ── Data Service ──────────────────────────────────────────────────────────────
data-build: ## Build l'image data-service
	$(COMPOSE) build data-service

data-start: ## Lance le data-service (port 5001)
	@echo "$(YELLOW)Démarrage data-service → http://localhost:5001$(NC)"
	$(COMPOSE) up -d --build data-service
	@echo "$(GREEN)✅ data-service : http://localhost:5001/docs$(NC)"

data-stop: ## Arrête le data-service
	$(COMPOSE) stop data-service

data-logs: ## Logs data-service en direct (Ctrl+C arrête le service)
	@trap '$(COMPOSE) stop data-service 2>/dev/null; echo "$(GREEN)data-service arrêté$(NC)"; exit 0' INT; \
	 $(COMPOSE) logs -f data-service

data-test: test-ds ## Tests data-service (alias → make test-ds)

data-shell: ## Shell dans le container data-service
	$(COMPOSE) exec data-service bash

# ── Dashboard ─────────────────────────────────────────────────────────────────
dashboard: ## Lance le dashboard agile + data-service sur :5050/:5001
	@echo "$(YELLOW)Démarrage MinIO + data-service (DVC)...$(NC)"
	@$(COMPOSE) up -d minio minio-init 2>/dev/null || true
	@sleep 6
	@$(COMPOSE) up -d --build data-service 2>/dev/null || echo "$(YELLOW)⚠ Docker non disponible — boutons DVC désactivés$(NC)"
	@echo "$(YELLOW)Dashboard DS_COVID → http://localhost:5050$(NC)"
	@echo "$(YELLOW)(Ctrl+C pour tout arrêter)$(NC)"
	@trap '$(COMPOSE) stop data-service minio 2>/dev/null; exit 0' INT; \
	 . .venv/bin/activate && cd dashboard && pip install -q -r requirements.txt && python app.py

clean-docker: ## Supprime les images et volumes Docker du projet
	$(COMPOSE) down -v --rmi local 2>/dev/null || true

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
