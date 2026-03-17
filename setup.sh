#!/usr/bin/env bash
# setup.sh -- DS_COVID MLOps
# Installation reproductible : detecte l'OS, propose dev ou user
#
# Usage :
#   ./setup.sh              -> interactif (demande dev ou user)
#   ./setup.sh --dev        -> mode developpeur (venv + deps)
#   ./setup.sh --user       -> mode utilisateur (Docker uniquement)
#   ./setup.sh --check      -> verifie l'etat sans installer
#   ./setup.sh --ci         -> mode CI (sans prompts interactifs)

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
REQUIREMENTS_FILE="${SCRIPT_DIR}/requirements/local.txt"

log()   { echo -e "${GREEN}[DS_COVID]${NC} $*"; }
warn()  { echo -e "${YELLOW}[DS_COVID]${NC} $*"; }
err()   { echo -e "${RED}[DS_COVID]${NC} $*"; exit 1; }
title() { echo -e "\n${BOLD}${BLUE}=== $* ===${NC}"; }

# -- Detection OS --------------------------------------------------------------
detect_os() {
    title "Detection de l'environnement"
    if [ -f /proc/version ] && grep -qi microsoft /proc/version 2>/dev/null; then
        OS="wsl"
        log "WSL (Linux sous Windows) detecte"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        log "Linux natif detecte"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        log "macOS detecte"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
        warn "Windows Git Bash detecte -- preferer WSL pour Docker"
    else
        OS="unknown"
        warn "OS non reconnu : $OSTYPE"
    fi
}

# -- Recherche Python valide (ignore Windows Store redirects) ------------------
find_python() {
    PYTHON_BIN=""
    for cmd in python3.12 python3.11 python3.10 python3 python; do
        if command -v "$cmd" &>/dev/null; then
            local pypath
            pypath="$(command -v "$cmd")"
            # Ignorer les redirects Windows Store dans WSL
            if echo "$pypath" | grep -qiE "WindowsApps|Microsoft/WindowsApps"; then
                warn "Ignore (Windows Store redirect) : $pypath"
                continue
            fi
            local major minor
            major="$("$cmd" -c 'import sys; print(sys.version_info[0])' 2>/dev/null)" || continue
            minor="$("$cmd" -c 'import sys; print(sys.version_info[1])' 2>/dev/null)" || continue
            if [ "${major:-0}" -ge 3 ] && [ "${minor:-0}" -ge 10 ]; then
                PYTHON_BIN="$cmd"
                log "Python trouve : $pypath ($major.$minor)"
                return 0
            else
                warn "$cmd trop ancien ($major.$minor), besoin >= 3.10"
            fi
        fi
    done
    return 1
}

# -- Installation Python (WSL/Linux seulement) --------------------------------
install_python() {
    if [ "$OS" = "wsl" ] || [ "$OS" = "linux" ]; then
        warn "Python >= 3.10 non trouve. Installer python3.11 maintenant ? [o/N]"
        read -r answer
        if [[ "$answer" =~ ^[oOyY]$ ]]; then
            log "Installation python3.11..."
            sudo apt-get update -qq
            sudo apt-get install -y python3.11 python3.11-venv python3.11-dev
            log "Python 3.11 installe."
        else
            err "Python >= 3.10 requis pour le mode dev. Installez-le puis relancez."
        fi
    elif [ "$OS" = "macos" ]; then
        if command -v brew &>/dev/null; then
            warn "Python >= 3.10 non trouve. Installer via Homebrew ? [o/N]"
            read -r answer
            if [[ "$answer" =~ ^[oOyY]$ ]]; then
                brew install python@3.11
            else
                err "Installez via : brew install python@3.11"
            fi
        else
            err "Python >= 3.10 requis. Installez depuis https://python.org"
        fi
    else
        err "Python >= 3.10 requis. Installez-le puis relancez setup.sh."
    fi
}

# -- Verification Docker -------------------------------------------------------
check_docker() {
    title "Verification Docker"
    if ! command -v docker &>/dev/null; then
        warn "Docker non trouve."
        if [ "$OS" = "wsl" ]; then
            warn "  -> Installez Docker Desktop sur Windows"
            warn "  -> Docker Desktop > Settings > Resources > WSL Integration > activez votre distro"
        fi
        return 1
    fi
    if ! docker info &>/dev/null 2>&1; then
        warn "Docker installe mais daemon non accessible."
        if [ "$OS" = "wsl" ]; then
            warn "  -> Ouvrez Docker Desktop sur Windows et attendez le demarrage"
            warn "  -> Docker Desktop > Settings > Resources > WSL Integration"
        fi
        return 1
    fi
    log "Docker OK : $(docker --version)"
    return 0
}

# -- Setup .env ----------------------------------------------------------------
setup_env() {
    title "Configuration .env"
    if [ ! -f "${SCRIPT_DIR}/.env" ]; then
        if [ -f "${SCRIPT_DIR}/.env.example" ]; then
            cp "${SCRIPT_DIR}/.env.example" "${SCRIPT_DIR}/.env"
            log ".env cree depuis .env.example"
            warn "  -> Editez .env si besoin (MODEL_PATH notamment)"
        else
            warn ".env.example absent, creation d'un .env minimal..."
            cat > "${SCRIPT_DIR}/.env" << 'ENVEOF'
# DS_COVID -- Variables d'environnement
BACKEND_URL=http://localhost:8000
MODEL_PATH=/app/data/models/best_model.keras
MLFLOW_TRACKING_URI=http://mlflow:5000
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
POSTGRES_USER=mlflow
POSTGRES_PASSWORD=mlflow
POSTGRES_DB=mlflow
ENVEOF
            log ".env minimal cree"
        fi
    else
        log ".env deja present -- non ecrase"
    fi
}

# -- Creer les dossiers --------------------------------------------------------
setup_dirs() {
    title "Creation des dossiers"
    mkdir -p "${SCRIPT_DIR}/data/models" \
             "${SCRIPT_DIR}/data/raw" \
             "${SCRIPT_DIR}/data/processed" \
             "${SCRIPT_DIR}/tmp/logs" \
             "${SCRIPT_DIR}/tmp/quality"
    touch "${SCRIPT_DIR}/data/models/.gitkeep" 2>/dev/null || true
    touch "${SCRIPT_DIR}/data/processed/.gitkeep" 2>/dev/null || true
    log "Dossiers data/ et tmp/ prets"
}

# -- Mode UTILISATEUR (Docker only) -------------------------------------------
setup_user() {
    echo ""
    echo -e "${BOLD}${BLUE}Mode UTILISATEUR${NC} -- Docker uniquement, aucun Python requis sur le host"
    echo ""
    setup_env
    setup_dirs
    echo ""
    if check_docker; then
        echo ""
        log "Environnement utilisateur pret !"
        echo ""
        echo -e "${BLUE}Pour demarrer :${NC}"
        echo "  make start       -> backend FastAPI uniquement"
        echo "  make start-all   -> stack complete (backend + frontend + mlflow + minio)"
    else
        echo ""
        warn "Environnement configure, mais Docker n'est pas accessible."
        warn "Demarrez Docker Desktop, puis : make start"
    fi
}

# -- Mode DEVELOPPEUR (Docker first, venv optionnel pour IDE) -----------------
setup_dev() {
    echo ""
    echo -e "${BOLD}${BLUE}Mode DEVELOPPEUR${NC} -- Docker (runtime principal) + venv leger optionnel (IDE)"
    echo ""

    # Docker requis pour le dev
    title "Verification Docker (requis)"
    if ! check_docker; then
        err "Docker requis pour le mode developpeur.\nInstallez Docker Desktop puis relancez."
    fi

    setup_env
    setup_dirs

    # Login GHCR (requis pour l'image de base covid-xray-base privee)
    title "Authentification GHCR"
    local BASE_IMAGE="ghcr.io/data-team-dst/covid-xray-base:latest"

    # Charger les variables du .env si present
    local env_file="${SCRIPT_DIR}/.env"
    local stored_token="" stored_user=""
    if [ -f "${env_file}" ]; then
        stored_token="$(grep -E '^GHCR_TOKEN=' "${env_file}" | cut -d= -f2- | tr -d '"' | tr -d "'")"
        stored_user="$(grep -E '^GHCR_USER=' "${env_file}" | cut -d= -f2- | tr -d '"' | tr -d "'")"
    fi

    # Tenter le login automatique si token disponible dans .env
    if [ -n "${stored_token}" ] && [ -n "${stored_user}" ]; then
        log "Token GHCR trouve dans .env -- tentative de connexion (${stored_user})..."
        if echo "${stored_token}" | docker login ghcr.io -u "${stored_user}" --password-stdin 2>/dev/null; then
            log "Connecte a GHCR via .env (${stored_user})"
        else
            warn "Token .env invalide ou expire -- veuillez vous reconnecter"
            stored_token=""
        fi
    fi

    # Verifier si l'image est accessible (apres eventuel login auto)
    if docker manifest inspect "${BASE_IMAGE}" &>/dev/null 2>&1; then
        log "Image de base accessible : ${BASE_IMAGE}"
    elif [ -z "${stored_token}" ]; then
        warn "Image de base privee : ${BASE_IMAGE}"
        warn "Une authentification GitHub est requise pour la telecharger."
        echo ""
        echo -e "${BLUE}Un Personal Access Token (PAT) GitHub est necessaire.${NC}"
        echo ""
        echo "  [1] J'ai deja un PAT        --> je le saisis maintenant"
        echo "  [2] Je n'ai pas de PAT      --> expliquez-moi comment en creer un"
        echo "  [3] Je ne sais pas ce c'est --> explication complete"
        echo "  [4] Ignorer                 --> builder sans le frontend (backend seul)"
        echo ""
        read -rp "Votre choix [1/2/3/4] : " pat_choice

        ghcr_do_login() {
            local user="$1" token="$2"
            if echo "${token}" | docker login ghcr.io -u "${user}" --password-stdin 2>/dev/null; then
                log "Connecte a GHCR en tant que ${user}"
                # Sauvegarde automatique dans .env (pas de prompt -- c'est le but)
                if grep -q '^GHCR_TOKEN=' "${env_file}"; then
                    sed -i "s|^GHCR_TOKEN=.*|GHCR_TOKEN=${token}|" "${env_file}"
                else
                    echo "GHCR_TOKEN=${token}" >> "${env_file}"
                fi
                if grep -q '^GHCR_USER=' "${env_file}"; then
                    sed -i "s|^GHCR_USER=.*|GHCR_USER=${user}|" "${env_file}"
                else
                    echo "GHCR_USER=${user}" >> "${env_file}"
                fi
                log "Credentials sauvegardes dans .env -- plus besoin de les resaisir"
                warn ".env est gitignore : vos credentials restent sur votre machine uniquement"
            else
                warn "Echec du login. Verifiez votre username GitHub et votre token."
            fi
        }

        case "$pat_choice" in
            1)
                echo ""
                read -rp "  GitHub username : " gh_user
                read -rsp "  GitHub PAT (ghp_...) : " gh_token
                echo ""
                ghcr_do_login "${gh_user}" "${gh_token}"
                ;;
            2)
                echo ""
                echo -e "${BLUE}Comment creer un PAT GitHub :${NC}"
                echo ""
                echo "  1. Ouvrez : https://github.com/settings/tokens"
                echo "  2. Cliquez 'Generate new token (classic)'"
                echo -e "  3. Nom OBLIGATOIRE : ${YELLOW}ds-covid-ghcr${NC}  <- copier-coller ce nom"
                echo "  4. Expiration : 90 days (recommande)"
                echo -e "  5. Cochez UNIQUEMENT : ${YELLOW}[x] read:packages${NC}  <- rien d'autre"
                echo "  6. Cliquez 'Generate token' -> copiez le token (commence par ghp_)"
                echo ""
                echo -e "${YELLOW}Gardez cet onglet GitHub ouvert, revenez ici une fois le token copie.${NC}"
                echo ""
                read -rp "Token copie, pret a le saisir ? [o/N] " now
                if [[ "$now" =~ ^[oOyY]$ ]]; then
                    read -rp "  Votre username GitHub : " gh_user
                    read -rsp "  Collez votre token (ghp_...) : " gh_token
                    echo ""
                    ghcr_do_login "${gh_user}" "${gh_token}"
                else
                    warn "Relancez ./setup.sh --dev une fois le token cree"
                fi
                ;;
            3)
                echo ""
                echo -e "${BLUE}C'est quoi un PAT (Personal Access Token) ?${NC}"
                echo ""
                echo "  GitHub est comme un coffre-fort de code. Pour que votre"
                echo "  machine puisse telecharger une image Docker privee hebergee"
                echo "  sur ce coffre (GHCR = GitHub Container Registry), elle doit"
                echo "  prouver que vous avez le droit d'y acceder."
                echo ""
                echo "  Un PAT = une cle speciale que GitHub vous genere."
                echo "  Vous la donnez UNE SEULE FOIS a ce script, il s'en souvient."
                echo ""
                echo -e "${BLUE}Comment en creer un (2 minutes) :${NC}"
                echo ""
                echo "  1. Ouvrez : https://github.com/settings/tokens"
                echo "  2. Cliquez 'Generate new token (classic)'"
                echo -e "  3. Nom OBLIGATOIRE : ${YELLOW}ds-covid-ghcr${NC}"
                echo "  4. Expiration : 90 days"
                echo -e "  5. Cochez UNIQUEMENT : ${YELLOW}[x] read:packages${NC}"
                echo "  6. Cliquez 'Generate token' -> copiez le token (ghp_...)"
                echo ""
                echo -e "${YELLOW}Revenez ici une fois le token copie.${NC}"
                echo ""
                read -rp "Token copie, pret a le saisir ? [o/N] " now
                if [[ "$now" =~ ^[oOyY]$ ]]; then
                    read -rp "  Votre username GitHub : " gh_user
                    read -rsp "  Collez votre token (ghp_...) : " gh_token
                    echo ""
                    ghcr_do_login "${gh_user}" "${gh_token}"
                else
                    warn "Relancez ./setup.sh --dev une fois le token cree"
                fi
                ;;
            4|*)
                warn "Authentification ignoree -- seul le backend sera construit"
                ;;
        esac
    fi

    # Build des images Docker localement
    title "Build des images Docker"
    log "docker compose build (backend + trainer + streamlit)..."
    if docker compose -f "${SCRIPT_DIR}/docker-compose.yml" build; then
        log "Images construites avec succes"
    else
        warn "Build partiel -- l'image de base GHCR est peut-etre inaccessible"
        warn "Backend seul disponible. Relancez apres : docker login ghcr.io"
    fi

    # Venv leger optionnel (ruff + pylint + pytest pour IDE/autocomplete)
    title "Venv leger pour IDE (optionnel)"
    echo -e "Voulez-vous un venv minimal pour l'autocomplete IDE (ruff, pylint) ?"
    echo -e "Non requis pour faire tourner le projet. [o/N]"
    read -r answer
    if [[ "$answer" =~ ^[oOyY]$ ]]; then
        if find_python; then
            if [ ! -d "${VENV_DIR}" ]; then
                "${PYTHON_BIN}" -m venv "${VENV_DIR}"
            fi
            "${VENV_DIR}/bin/pip" install -q --upgrade pip
            "${VENV_DIR}/bin/pip" install -q ruff pylint pytest pytest-cov
            log "Venv IDE installe : ruff, pylint, pytest"
            log "Pointez votre IDE vers : ${VENV_DIR}/bin/python"
        else
            warn "Python non trouve sur le host -- venv IDE ignore"
        fi
    else
        log "Venv IDE ignore"
    fi

    echo ""
    echo -e "${BOLD}${GREEN}============================="
    echo -e "  Setup developpeur termine !"
    echo -e "=============================${NC}"
    echo ""
    echo -e "Commandes principales :"
    echo -e "  ${YELLOW}make start${NC}             -> backend FastAPI (Docker)"
    echo -e "  ${YELLOW}make start-all${NC}         -> stack complete (backend + frontend + mlflow)"
    echo -e "  ${YELLOW}make test${NC}              -> tests dans Docker"
    echo -e "  ${YELLOW}make lint${NC}              -> linting dans Docker"
    echo -e "  ${YELLOW}make build${NC}             -> rebuild les images"
    echo -e "  ${YELLOW}./setup.sh --check${NC}     -> verifier l'environnement"
    echo ""
    echo -e "${BLUE}Edition du code :${NC} modifiez directement backend/app, frontend, src/"
    echo -e "Les volumes Docker sont montes -> rechargement automatique (uvicorn --reload)"
    echo ""
}

# -- Mode CHECK ----------------------------------------------------------------
setup_check() {
    title "Verification de l'environnement DS_COVID"
    local ok=true

    detect_os

    # Python systeme
    title "Python systeme"
    if find_python; then
        log "Python systeme : OK"
    else
        warn "Python >= 3.10 : NON TROUVE (necessaire pour mode dev)"
        ok=false
    fi

    # Venv
    title "Environnement virtuel"
    if [ -d "${VENV_DIR}" ]; then
        log "Venv (.venv) : OK"
        for pkg in fastapi uvicorn streamlit pytest ruff; do
            if "${VENV_DIR}/bin/pip" show "$pkg" &>/dev/null 2>&1; then
                log "  $pkg : OK"
            else
                warn "  $pkg : ABSENT"
                ok=false
            fi
        done
    else
        warn "Venv (.venv) : ABSENT -> lancez ./setup.sh --dev"
        ok=false
    fi

    # .env
    title "Configuration"
    if [ -f "${SCRIPT_DIR}/.env" ]; then
        log ".env : OK"
    else
        warn ".env : ABSENT (sera cree au premier ./setup.sh)"
        ok=false
    fi

    # Dossiers data/
    title "Dossiers data/"
    for d in data/raw data/processed data/models; do
        if [ -d "${SCRIPT_DIR}/${d}" ]; then
            log "  $d : OK"
        else
            warn "  $d : ABSENT"
            ok=false
        fi
    done

    # Modele
    local model_count
    model_count=$(ls "${SCRIPT_DIR}/data/models/"*.keras 2>/dev/null | wc -l)
    if [ "$model_count" -gt 0 ]; then
        log "  Modele .keras : $model_count fichier(s)"
    else
        warn "  Modele .keras : ABSENT -- /predict retournera 503 (normal Phase 1)"
    fi

    # Docker
    check_docker || true

    echo ""
    if [ "$ok" = true ]; then
        log "Environnement pret. Lancez : ./start_local.sh"
    else
        warn "Problemes detectes. Lancez : ./setup.sh"
    fi
}

# -- Main ----------------------------------------------------------------------
echo ""
echo -e "${BOLD}${GREEN}================================="
echo -e "  DS_COVID -- Setup environnement"
echo -e "=================================${NC}"
echo ""

detect_os

MODE="${1:-ask}"

case "$MODE" in
    --dev)
        setup_dev
        ;;
    --user)
        setup_user
        ;;
    --check)
        setup_check
        ;;
    --ci)
        # Mode CI : comme --dev mais sans prompts interactifs
        find_python || err "Python >= 3.10 requis en CI"
        if [ ! -d "${VENV_DIR}" ]; then
            "${PYTHON_BIN}" -m venv "${VENV_DIR}"
        fi
        "${VENV_DIR}/bin/pip" install -q --upgrade pip wheel setuptools
        "${VENV_DIR}/bin/pip" install -q -r "${REQUIREMENTS_FILE}"
        setup_dirs
        if [ ! -f "${SCRIPT_DIR}/.env" ] && [ -f "${SCRIPT_DIR}/.env.example" ]; then
            cp "${SCRIPT_DIR}/.env.example" "${SCRIPT_DIR}/.env"
        fi
        log "Setup CI termine"
        ;;
    ask|*)
        echo -e "${BLUE}Quel mode souhaitez-vous ?${NC}"
        echo ""
        echo "  [1] Developpeur  -- venv Python + tests + linting + demarrage local"
        echo "               (necessite Python >= 3.10 sur le host)"
        echo ""
        echo "  [2] Utilisateur  -- Docker uniquement, aucun Python requis"
        echo "               (start-docker / make start-all)"
        echo ""
        read -rp "Votre choix [1/2] : " choice
        case "$choice" in
            1) setup_dev  ;;
            2) setup_user ;;
            *) warn "Choix invalide. Relancez avec --dev ou --user"; exit 1 ;;
        esac
        ;;
esac
