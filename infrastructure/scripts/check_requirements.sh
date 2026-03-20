#!/bin/bash
# check_requirements.sh — Vérifie que chaque package déclaré est importé dans le code
# Optimisé : un seul grep pour indexer tous les imports, puis lookup O(1) en mémoire
# Usage : bash infrastructure/scripts/check_requirements.sh [--strict]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$PROJECT_ROOT"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m'

STRICT=false
[[ "${1:-}" == "--strict" ]] && STRICT=true

SCAN_DIRS=(backend/app frontend backend/src)

ARTIFACT_DIR="tmp/quality"
mkdir -p "$ARTIFACT_DIR"
REQ_REPORT="$ARTIFACT_DIR/requirements.txt"
REQ_SCORE_FILE="$ARTIFACT_DIR/requirements_score.txt"
> "$REQ_REPORT"

# ── Catégorie 1 : outils (runners, linters, CLI) ──────────────────────────────
TOOL_PACKAGES=(
    black isort ruff pylint
    pytest pytest_cov
    jupyterlab uvicorn dvc
    contourpy cycler fonttools kiwisolver packaging
    pyparsing python_dateutil pytz six threadpoolctl tzdata
)

# ── Catégorie 2 : dépendances implicites de frameworks ────────────────────────
IMPLICIT_PACKAGES=(
    python_multipart   # FastAPI : form data / file uploads
    httpx              # FastAPI TestClient interne
    python_dotenv      # pydantic-settings interne
    requests           # streamlit / DVC interne
)

# ── Mapping pip name → import name ────────────────────────────────────────────
declare -A ALIASES=(
    [scikit_learn]=sklearn
    [scikit_image]=skimage
    [opencv_python]=cv2
    [opencv_contrib_python]=cv2
    [pillow]=PIL
    [pydantic_settings]=pydantic_settings
    [streamlit_extras]=streamlit_extras
    [imbalanced_learn]=imblearn
)

# ── Fonctions ─────────────────────────────────────────────────────────────────
normalize() {
    echo "$1" | sed 's/[><=!].*//' | sed 's/\[.*//' \
              | tr '[:upper:]' '[:lower:]' | tr -- '-' '_' \
              | tr -d ' \t\r'
}

import_name_of() {
    local norm
    norm=$(normalize "$1")
    [[ -n "${ALIASES[$norm]+_}" ]] && echo "${ALIASES[$norm]}" && return
    echo "$norm"
}

in_list() {
    local norm
    norm=$(normalize "$1")
    shift
    for item in "$@"; do
        [[ "$(normalize "$item")" == "$norm" ]] && return 0
    done
    return 1
}

# ── Index unique : UN SEUL grep sur toutes les sources ────────────────────────
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Vérification requirements (imports)${NC}"
echo -e "${GREEN}========================================${NC}"
printf "Indexation des imports dans %s ... " "${SCAN_DIRS[*]}"

IMPORT_INDEX=""
for dir in "${SCAN_DIRS[@]}"; do
    [ -d "$dir" ] || continue
    IMPORT_INDEX+=$(
        grep -rh --include="*.py" \
            --exclude-dir=__pycache__ --exclude-dir=.venv \
            -E "^[[:space:]]*(import|from)[[:space:]]+[a-zA-Z_][a-zA-Z0-9_]+" \
            "$dir" 2>/dev/null \
        | grep -oE "(import|from)[[:space:]]+[a-zA-Z_][a-zA-Z0-9_]+" \
        | awk '{print $2}'
    )
    IMPORT_INDEX+=$'\n'
done
# Dédoublonner
IMPORT_INDEX=$(echo "$IMPORT_INDEX" | sort -u)
echo -e "${GREEN}OK${NC}"

is_imported() {
    echo "$IMPORT_INDEX" | grep -q "^${1}$"
}

# ── Helpers rapport ───────────────────────────────────────────────────────────
log_both() { echo -e "$1"; echo "$2" >> "$REQ_REPORT"; }

# ── Analyse des fichiers requirements ─────────────────────────────────────────
TOTAL_UNUSED=0
TOTAL_USED=0
TOTAL_SKIPPED=0
UNUSED_SUMMARY=""   # accumule "fichier:package" pour le récap final

{
    echo "========================================"
    echo "ANALYSE REQUIREMENTS — IMPORTS MANQUANTS"
    echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Scan : ${SCAN_DIRS[*]}"
    echo "========================================"
} >> "$REQ_REPORT"

for req_file in requirements/*.txt; do
    [ -f "$req_file" ] || continue
    echo -e "\n${CYAN}📄 $(basename "$req_file")${NC}"
    echo "" >> "$REQ_REPORT"
    echo "📄 $(basename "$req_file")" >> "$REQ_REPORT"

    while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line%$'\r'}"
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]]           && continue
        [[ "$line" =~ ^-r ]]            && continue

        pkg_display=$(echo "$line" | sed 's/[><=!].*//' | sed 's/\[.*//' | tr -d ' \t\r')
        [[ -z "$pkg_display" ]] && continue

        if in_list "$line" "${TOOL_PACKAGES[@]}"; then
            TOTAL_SKIPPED=$((TOTAL_SKIPPED + 1))
            echo -e "   ${GRAY}⏭  ${pkg_display}${NC}  (outil)"
            echo "   [outil]    ${pkg_display}" >> "$REQ_REPORT"
            continue
        fi

        if in_list "$line" "${IMPLICIT_PACKAGES[@]}"; then
            TOTAL_SKIPPED=$((TOTAL_SKIPPED + 1))
            echo -e "   ${YELLOW}🔗 ${pkg_display}${NC}  (dépendance implicite framework)"
            echo "   [implicite] ${pkg_display}" >> "$REQ_REPORT"
            continue
        fi

        iname=$(import_name_of "$line")

        if is_imported "$iname"; then
            TOTAL_USED=$((TOTAL_USED + 1))
            echo -e "   ${GREEN}✅ ${pkg_display}${NC}  →  import ${iname}"
            echo "   [OK]       ${pkg_display}  →  import ${iname}" >> "$REQ_REPORT"
        else
            TOTAL_UNUSED=$((TOTAL_UNUSED + 1))
            echo -e "   ${RED}❌ ${pkg_display}${NC}  →  '${iname}' introuvable dans les sources"
            echo "   [MANQUANT] ${pkg_display}  →  '${iname}' introuvable dans les sources" >> "$REQ_REPORT"
            UNUSED_SUMMARY+="$(basename "$req_file"):${pkg_display}"$'\n'
        fi

    done < "$req_file"
done

{
    echo ""
    echo "========================================"
    echo "  Utilisés : ${TOTAL_USED}  |  Skip : ${TOTAL_SKIPPED}  |  Inutilisés : ${TOTAL_UNUSED}"
    echo "========================================"
} >> "$REQ_REPORT"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "  Utilisés : ${TOTAL_USED}  |  Skip : ${TOTAL_SKIPPED}  |  Inutilisés : ${TOTAL_UNUSED}"
echo -e "${GREEN}========================================${NC}"

# Écrire le score pour check_quality.sh
echo "${TOTAL_UNUSED}" > "$REQ_SCORE_FILE"

if [ "$TOTAL_UNUSED" -eq 0 ]; then
    echo -e "${GREEN}✅ Requirements OK${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  ${TOTAL_UNUSED} package(s) sans import détecté :${NC}"
    echo "" >> "$REQ_REPORT"
    echo "⚠️  ${TOTAL_UNUSED} package(s) sans import détecté :" >> "$REQ_REPORT"
    # Afficher groupé par fichier
    _prev_file=""
    while IFS=: read -r _file _pkg; do
        [[ -z "$_file" ]] && continue
        if [[ "$_file" != "$_prev_file" ]]; then
            echo -e "   ${CYAN}${_file}${NC}"
            echo "   ${_file}" >> "$REQ_REPORT"
            _prev_file="$_file"
        fi
        echo -e "     ${RED}→ ${_pkg}${NC}"
        echo "     → ${_pkg}" >> "$REQ_REPORT"
    done <<< "$UNUSED_SUMMARY"
    echo -e "${YELLOW}→ Vérifier usage CLI/notebook/transitif avant de retirer${NC}"
    echo "→ Vérifier usage CLI/notebook/transitif avant de retirer" >> "$REQ_REPORT"
    [ "$STRICT" = true ] && exit 1
    exit 0
fi
