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
#   make dvc-repro  → lance `dvc repro` dans le container trainer (GPU, sans dvc local)

.PHONY: all setup setup-check setup-be setup-ds setup-dvc setup-fe setup-dashboard setup-segmentation start start-local start-docker start-all \
        stop restart logs logs-all test test-be test-ds test-dvc test-segmentation verify lint fix clean build shell help dashboard \
        data-build data-start data-stop data-logs data-test data-shell \
        dvc-build dvc-start dvc-stop dvc-logs dvc-shell \
        dvc-setup dvc-setup-dagshub dvc-push dvc-pull dvc-push-dagshub dvc-pull-dagshub dvc-repro load-test setup-load-test

# ── Couleurs ──────────────────────────────────────────────────────────────────
GREEN  := \033[0;32m
YELLOW := \033[1;33m
RED    := \033[0;31m
NC     := \033[0m

# ── Variables ─────────────────────────────────────────────────────────────────
BACKEND_URL  := http://localhost:8000
FRONTEND_URL := http://localhost:8501
PYTHON       := python3
SCRIPTS      := ops
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
# .dvc/config.local (gitignoré) peut contenir plusieurs sections [remote "..."] —
# chaque cible dvc-setup* ne touche qu'à SA section (strip-puis-append) pour ne pas
# écraser les credentials d'un autre remote déjà configuré.
dvc-setup: ## Configure DVC remote MinIO (credentials locaux, gitignorés)
	@echo "$(YELLOW)Configuration DVC remote MinIO...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)⚠ .env introuvable — copie .env.example puis renseigne les variables MinIO$(NC)"; \
		exit 1; \
	fi
	@set -a && . ./.env && set +a && \
	access_key_id="$${MINIO_ROOT_USER:-minio}" && \
	secret_access_key="$${MINIO_ROOT_PASSWORD:-minio123}" && \
	touch .dvc/config.local && \
	awk '$$0=="[remote \"minio\"]"{skip=1;next} /^\[/{skip=0} !skip' .dvc/config.local > .dvc/config.local.tmp && mv .dvc/config.local.tmp .dvc/config.local && \
	{ echo "[remote \"minio\"]"; echo "    access_key_id = $$access_key_id"; echo "    secret_access_key = $$secret_access_key"; } >> .dvc/config.local
	@echo "$(GREEN)✅ .dvc/config.local créé (remote minio)$(NC)"

dvc-setup-dagshub: ## Configure DVC remote DagsHub (credentials locaux, gitignorés, lus depuis .env)
	@if [ ! -f .env ]; then \
		echo "$(RED)⚠ .env introuvable — copie .env.example puis renseigne REMOTE_S3_ACCESS_KEY/REMOTE_S3_SECRET_KEY (token DagsHub, dagshub.com → Settings → Tokens)$(NC)"; \
		exit 1; \
	fi
	@set -a && . ./.env && set +a && \
	if [ -z "$$REMOTE_S3_ACCESS_KEY" ] || [ "$$REMOTE_S3_ACCESS_KEY" = "put_token_here" ]; then \
		echo "$(RED)⚠ REMOTE_S3_ACCESS_KEY non renseigné dans .env (token DagsHub)$(NC)"; \
		exit 1; \
	fi && \
	touch .dvc/config.local && \
	awk '$$0=="[remote \"dagshub\"]"{skip=1;next} /^\[/{skip=0} !skip' .dvc/config.local > .dvc/config.local.tmp && mv .dvc/config.local.tmp .dvc/config.local && \
	{ echo "[remote \"dagshub\"]"; echo "    access_key_id = $$REMOTE_S3_ACCESS_KEY"; echo "    secret_access_key = $$REMOTE_S3_SECRET_KEY"; } >> .dvc/config.local && \
	awk '$$0=="[remote \"dagshub-storage\"]"{skip=1;next} /^\[/{skip=0} !skip' .dvc/config.local > .dvc/config.local.tmp && mv .dvc/config.local.tmp .dvc/config.local && \
	{ echo "[remote \"dagshub-storage\"]"; echo "    password = $$REMOTE_S3_ACCESS_KEY"; } >> .dvc/config.local
	@echo "$(GREEN)✅ .dvc/config.local mis à jour (remotes dagshub + dagshub-storage)$(NC)"

dvc-push: setup-dvc dvc-setup ## Pousse les données vers MinIO (make start-all requis)
	@echo "$(YELLOW)Push DVC → MinIO...$(NC)"
	@dvc-service/.venv/bin/dvc push
	@echo "$(GREEN)✅ Données pushées$(NC)"

dvc-pull: setup-dvc ## Récupère les données depuis MinIO
	@echo "$(YELLOW)Pull DVC ← MinIO...$(NC)"
	@dvc-service/.venv/bin/dvc pull
	@echo "$(GREEN)✅ Données récupérées$(NC)"

dvc-push-dagshub: setup-dvc dvc-setup-dagshub ## Pousse les données/modèles vers DagsHub (bucket S3 + DagsHub Storage natif)
	@echo "$(YELLOW)Push DVC → DagsHub (bucket S3)...$(NC)"
	@dvc-service/.venv/bin/dvc push -r dagshub
	@echo "$(YELLOW)Push DVC → DagsHub Storage (natif — nécessaire pour la prévisualisation sur dagshub.com)...$(NC)"
	@dvc-service/.venv/bin/dvc push -r dagshub-storage
	@echo "$(GREEN)✅ Données pushées vers DagsHub$(NC)"

dvc-pull-dagshub: setup-dvc dvc-setup-dagshub ## Récupère les données/modèles depuis DagsHub (dvc pull -r dagshub)
	@echo "$(YELLOW)Pull DVC ← DagsHub...$(NC)"
	@dvc-service/.venv/bin/dvc pull -r dagshub
	@echo "$(GREEN)✅ Données récupérées depuis DagsHub$(NC)"

dvc-repro: ## Lance dvc repro dans le container trainer (GPU + dvc préinstallés, pas besoin de dvc en local)
	@echo "$(YELLOW)dvc repro dans le container trainer (GPU)...$(NC)"
	$(COMPOSE) --profile training run --rm --build \
		-v "$$(pwd):/app" -w /app \
		trainer dvc repro
	@echo "$(GREEN)✅ Pipeline DVC rejoué$(NC)"

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
	@backend/.venv/bin/pip install -q --require-hashes -r backend/requirements-dev.txt
	@echo "$(GREEN)✅ backend/.venv prêt$(NC)"

setup-ds: ## Crée/met à jour le venv data-service (data-service/.venv)
	@if [ ! -f data-service/.venv/bin/python ]; then \
		echo "$(YELLOW)Création venv data-service...$(NC)"; \
		$(PYTHON) -m venv data-service/.venv; \
	fi
	@echo "$(YELLOW)Installation deps data-service...$(NC)"
	@data-service/.venv/bin/pip install -q --require-hashes \
		-r data-service/requirements.txt \
		-r data-service/dev-requirements.txt
	@echo "$(GREEN)✅ data-service/.venv prêt$(NC)"

setup-dvc: ## Crée/met à jour le venv dvc-service (dvc-service/.venv) — CLI dvc pour les cibles dvc-*
	@if [ ! -f dvc-service/.venv/bin/python ]; then \
		echo "$(YELLOW)Création venv dvc-service...$(NC)"; \
		$(PYTHON) -m venv dvc-service/.venv; \
	fi
	@echo "$(YELLOW)Installation deps dvc-service...$(NC)"
	@dvc-service/.venv/bin/pip install -q --require-hashes \
		-r dvc-service/requirements.txt \
		-r dvc-service/dev-requirements.txt
	@echo "$(GREEN)✅ dvc-service/.venv prêt$(NC)"

setup-fe: ## Crée/met à jour le venv frontend (frontend/.venv)
	@if [ -d frontend/.venv/Scripts ] && [ ! -f frontend/.venv/bin/python ]; then \
		echo "$(RED)⚠ venv Windows détecté — suppression et recréation depuis WSL$(NC)"; \
		rm -rf frontend/.venv; \
	fi
	@if [ ! -f frontend/.venv/bin/python ]; then \
		echo "$(YELLOW)Création venv frontend...$(NC)"; \
		$(PYTHON) -m venv frontend/.venv; \
	fi
	@echo "$(YELLOW)Installation deps frontend...$(NC)"
	@frontend/.venv/bin/pip install -q --require-hashes -r frontend/requirements-dev.txt
	@echo "$(GREEN)✅ frontend/.venv prêt$(NC)"

setup-segmentation: ## Crée/met à jour le venv segmentation-service (segmentation-service/.venv)
	@if [ ! -f segmentation-service/.venv/bin/python ]; then \
		echo "$(YELLOW)Création venv segmentation-service...$(NC)"; \
		$(PYTHON) -m venv segmentation-service/.venv; \
	fi
	@echo "$(YELLOW)Installation deps segmentation-service...$(NC)"
	@segmentation-service/.venv/bin/pip install -q --require-hashes \
		-r segmentation-service/requirements.txt \
		-r segmentation-service/dev-requirements.txt
	@echo "$(GREEN)✅ segmentation-service/.venv prêt$(NC)"

setup-dashboard: ## Crée/met à jour le venv dashboard (dashboard/.venv)
	@if [ -d dashboard/.venv/Scripts ] && [ ! -f dashboard/.venv/bin/python ]; then \
		echo "$(RED)⚠ venv Windows détecté — suppression et recréation depuis WSL$(NC)"; \
		rm -rf dashboard/.venv; \
	fi
	@if [ ! -f dashboard/.venv/bin/python ]; then \
		echo "$(YELLOW)Création venv dashboard...$(NC)"; \
		$(PYTHON) -m venv dashboard/.venv; \
	fi
	@echo "$(YELLOW)Installation deps dashboard...$(NC)"
	@dashboard/.venv/bin/pip install -q --require-hashes -r dashboard/requirements.txt
	@echo "$(GREEN)✅ dashboard/.venv prêt$(NC)"

# ── Tests ─────────────────────────────────────────────────────────────────────
test: test-be test-ds test-dvc test-segmentation ## Lance les tests de tous les microservices (venvs isolés)

test-be: setup-be ## Tests backend dans son venv isolé
	@echo "$(YELLOW)── Tests backend ──────────────────────────────────────$(NC)"
	@PYTHONPATH=. backend/.venv/bin/python -m pytest backend/tests/ -v \
		--cov=backend/app \
		--cov-report=term-missing \
		--cov-report=xml:backend/coverage.xml \
		--cov-fail-under=80
	@echo "$(GREEN)✅ Tests backend OK$(NC)"

test-ds: setup-ds ## Tests data-service dans son venv isolé
	@echo "$(YELLOW)── Tests data-service ─────────────────────────────────$(NC)"
	@cd data-service && PYTHONPATH=src:.. .venv/bin/python -m pytest tests/ -v \
		--cov=data_service \
		--cov-report=term-missing \
		--cov-report=xml:ds-coverage.xml \
		--cov-fail-under=80
	@echo "$(GREEN)✅ Tests data-service OK$(NC)"

test-dvc: setup-dvc ## Tests dvc-service dans son venv isolé
	@echo "$(YELLOW)── Tests dvc-service ───────────────────────────────────$(NC)"
	@cd dvc-service && PYTHONPATH=src:.. .venv/bin/python -m pytest tests/ -v \
		--cov=dvc_service \
		--cov-report=term-missing \
		--cov-report=xml:coverage.xml \
		--cov-fail-under=80
	@echo "$(GREEN)✅ Tests dvc-service OK$(NC)"

test-segmentation: setup-segmentation ## Tests segmentation-service dans son venv isolé
	@echo "$(YELLOW)── Tests segmentation-service ─────────────────────────$(NC)"
	@cd segmentation-service && PYTHONPATH=src:.. .venv/bin/python -m pytest tests/ -v \
		--cov=segmentation_service \
		--cov-report=term-missing \
		--cov-report=xml:coverage.xml \
		--cov-fail-under=80
	@echo "$(GREEN)✅ Tests segmentation-service OK$(NC)"

test-docker: ## Lance les tests dans le container Docker
	docker compose exec backend pytest tests/ -v --cov=app

verify: ## Lance start-all puis vérifie toutes les US (démo tuteur)
	@echo "$(YELLOW)Démarrage de la stack (premier build peut prendre 3-5 min)...$(NC)"
	@$(COMPOSE) up -d --build 2>/dev/null || true
	@echo "$(YELLOW)Attente que backend soit healthy (max 120s)...$(NC)"
	@timeout=120; elapsed=0; \
	 while ! curl -sf http://localhost:8000/health > /dev/null 2>&1; do \
	   sleep 5; elapsed=$$((elapsed + 5)); \
	   printf "."; \
	   [ $$elapsed -ge $$timeout ] && echo " ⚠ Timeout backend" && break; \
	 done; echo ""
	@echo "$(YELLOW)Attente que MLflow soit healthy (max 180s — build + db upgrade)...$(NC)"
	@timeout=180; elapsed=0; \
	 while ! curl -sf http://localhost:5000 > /dev/null 2>&1; do \
	   sleep 5; elapsed=$$((elapsed + 5)); \
	   printf "."; \
	   [ $$elapsed -ge $$timeout ] && echo " ⚠ Timeout MLflow" && break; \
	 done; echo ""
	@bash verify.sh

# ── Load test ─────────────────────────────────────────────────────────────────
setup-load-test: ## Crée/met à jour le venv load-test (scripts/load_test/.venv)
	@if [ -d scripts/load_test/.venv/Scripts ] && [ ! -f scripts/load_test/.venv/bin/python ]; then \
		echo "$(RED)⚠ venv Windows détecté — suppression et recréation depuis WSL$(NC)"; \
		rm -rf scripts/load_test/.venv; \
	fi
	@if [ ! -f scripts/load_test/.venv/bin/python ]; then \
		echo "$(YELLOW)Création venv load-test...$(NC)"; \
		$(PYTHON) -m venv scripts/load_test/.venv; \
	fi
	@echo "$(YELLOW)Installation deps load-test...$(NC)"
	@scripts/load_test/.venv/bin/pip install -q --require-hashes -r scripts/load_test/requirements.txt
	@echo "$(GREEN)✅ scripts/load_test/.venv prêt$(NC)"

load-test: setup-load-test ## Test de charge locust sur /predict — 10 req/s, P95<500ms (nécessite un modèle chargé)
	@mkdir -p outputs/load_test
	@echo "$(YELLOW)Redémarrage backend avec rate limit relevé pour le test de charge...$(NC)"
	@RATE_LIMIT_PER_MINUTE=2000 $(COMPOSE) up -d --force-recreate backend
	@echo "$(YELLOW)Attente backend healthy (max 60s)...$(NC)"
	@timeout=60; elapsed=0; \
	 while ! curl -sf $(BACKEND_URL)/health > /dev/null 2>&1; do \
	   sleep 3; elapsed=$$((elapsed + 3)); \
	   printf "."; \
	   [ $$elapsed -ge $$timeout ] && echo " ⚠ Timeout backend" && break; \
	 done; echo ""
	@scripts/load_test/.venv/bin/locust -f scripts/load_test/locustfile.py --headless \
	   -u 10 -r 10 --run-time 1m --host $(BACKEND_URL) \
	   --html outputs/load_test/report.html --csv outputs/load_test/report
	@echo "$(GREEN)✅ Rapport : outputs/load_test/report.html$(NC)"
	@echo "$(YELLOW)Restauration du rate limit normal (RATE_LIMIT_PER_MINUTE de .env)...$(NC)"
	@$(COMPOSE) up -d --force-recreate backend

# ── Qualité ───────────────────────────────────────────────────────────────────
lint: setup-be ## Vérifie la qualité du code (ruff + pylint + structure)
	@echo "$(YELLOW)Vérification qualité...$(NC)"
	@bash $(SCRIPTS)/check_quality.sh --skip-pylint

lint-full: setup-be setup-fe ## Vérification qualité complète (avec pylint)
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

# ── DVC Service (opérations : status/pull/push/repro, cf. chantier point 16) ──
dvc-build: ## Build l'image dvc-service
	$(COMPOSE) build dvc-service

dvc-start: ## Lance le dvc-service (port 5003)
	@echo "$(YELLOW)Démarrage dvc-service → http://localhost:5003$(NC)"
	$(COMPOSE) up -d --build dvc-service
	@echo "$(GREEN)✅ dvc-service : http://localhost:5003/docs$(NC)"

dvc-stop: ## Arrête le dvc-service
	$(COMPOSE) stop dvc-service

dvc-logs: ## Logs dvc-service en direct (Ctrl+C arrête le service)
	@trap '$(COMPOSE) stop dvc-service 2>/dev/null; echo "$(GREEN)dvc-service arrêté$(NC)"; exit 0' INT; \
	 $(COMPOSE) logs -f dvc-service

dvc-shell: ## Shell dans le container dvc-service
	$(COMPOSE) exec dvc-service bash

# ── Dashboard ─────────────────────────────────────────────────────────────────
dashboard: setup-dashboard ## Lance le dashboard agile + data-service/dvc-service sur :5050/:5001/:5003
	@echo "$(YELLOW)Démarrage MinIO + data-service + dvc-service...$(NC)"
	@$(COMPOSE) up -d minio minio-init 2>/dev/null || true
	@sleep 6
	@$(COMPOSE) up -d --build data-service dvc-service 2>/dev/null || echo "$(YELLOW)⚠ Docker non disponible — boutons DVC désactivés$(NC)"
	@echo "$(YELLOW)Dashboard DS_COVID → http://localhost:5050$(NC)"
	@echo "$(YELLOW)(Ctrl+C pour tout arrêter)$(NC)"
	@trap '$(COMPOSE) stop data-service dvc-service minio 2>/dev/null; exit 0' INT; \
	 cd dashboard && .venv/bin/python app.py

clean-docker: ## Supprime les images et volumes Docker du projet
	$(COMPOSE) down -v --rmi local 2>/dev/null || true


# ── Monitoring (Phase 4 — Prometheus / Grafana) ─────────────────────────────
monitoring-start: ## Lance Prometheus + Grafana (nécessite backend démarré)
	@echo "$(YELLOW)Démarrage backend (requis pour le scraping)...$(NC)"
	@$(COMPOSE) up -d --build backend
	@echo "$(YELLOW)Démarrage Prometheus + Grafana...$(NC)"
	@$(COMPOSE) --profile monitoring up -d prometheus grafana
	@echo "$(GREEN)✅ Monitoring disponible :$(NC)"
	@echo "   Prometheus : http://localhost:9090"
	@echo "   Grafana    : http://localhost:3000  (admin / admin par défaut)"
 
monitoring-stop: ## Arrête Prometheus + Grafana
	@echo "$(YELLOW)Arrêt de Prometheus + Grafana...$(NC)"
	$(COMPOSE) --profile monitoring stop prometheus grafana
	@echo "$(GREEN)✅ Monitoring arrêté$(NC)"
 
monitoring-logs: ## Logs Prometheus + Grafana en direct (Ctrl+C arrête les services)
	@trap '$(COMPOSE) --profile monitoring stop prometheus grafana 2>/dev/null; exit 0' INT; \
	 $(COMPOSE) --profile monitoring logs -f prometheus grafana
 
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
