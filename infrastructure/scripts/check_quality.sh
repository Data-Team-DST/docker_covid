#!/bin/bash
# check_quality.sh - Vérification qualité alignée CI/CD Sanofi
# Usage: ./check_quality.sh [--skip-sonar] [--skip-pylint]

set -e

# Répertoire du script (pour référencer les scripts voisins)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Détection Python (WSL/Linux/Git Bash/Windows)
if command -v python3 &>/dev/null && python3 -c "import sys; sys.exit(0)" 2>/dev/null; then
    PYTHON3=python3
elif command -v python &>/dev/null && python -c "import sys; sys.exit(0)" 2>/dev/null; then
    PYTHON3=python
else
    # Fallback Windows Python
    for _py in \
        "/c/Users/steve/AppData/Local/Programs/Python/Python312/python.exe" \
        "/c/Users/steve/AppData/Local/Programs/Python/Python311/python.exe" \
        "/usr/bin/python3" "/usr/local/bin/python3"; do
        if [ -x "$_py" ]; then PYTHON3="$_py"; break; fi
    done
fi

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

COVERAGE_THRESHOLD=30
SKIP_SONAR=false
SKIP_PYLINT=false

# =========================
# Seuils de complexité
# =========================
MAX_FILES_PER_DIR=15
MAX_DEPTH=5
MAX_SUBDIRS_PER_DIR=8
MAX_LINES_PER_FILE=100

# =========================
# Dossiers artefacts projet
# =========================
ARTIFACT_DIR="./tmp/quality"
CACHE_DIR="./tmp/quality/.cache"
mkdir -p "$ARTIFACT_DIR" "$CACHE_DIR"

RUFF_REPORT="$ARTIFACT_DIR/ruff.txt"
PYLINT_FE_LOG="$ARTIFACT_DIR/pylint_fe.log"
PYLINT_BE_LOG="$ARTIFACT_DIR/pylint_be.log"
PYTEST_LOG="$ARTIFACT_DIR/pytest.log"
STRUCTURE_REPORT="$ARTIFACT_DIR/structure_complexity.txt"
CODE_SMELL_REPORT="$ARTIFACT_DIR/code_smell.txt"
SUMMARY="$ARTIFACT_DIR/summary.txt"

> "$SUMMARY"

# =========================
# Système de cache par hash
# =========================
# Calcule une clé de cache basée sur les timestamps + tailles (pas le contenu)
# find -printf lit les métadonnées inode → ~10x plus rapide que sha256sum du contenu
cache_key() {
    find "$@" -name "*.py" -not -path "*/__pycache__/*" \
        -printf "%T@ %s %p\n" 2>/dev/null \
        | sort | md5sum | cut -c1-16
}

# Lit une valeur depuis le cache (retourne 1 si absent/expiré)
cache_get() {
    local key="$1" file="$CACHE_DIR/${1}.cache"
    [ -f "$file" ] && cat "$file" && return 0
    return 1
}

# Écrit une valeur dans le cache
cache_set() {
    echo "$2" > "$CACHE_DIR/${1}.cache"
}

# Affiche [CACHE] si la valeur vient du cache
CACHE_HIT=false

# Préférer le Python du venv pour éviter les problèmes de shebang Windows/WSL
VENV_PYTHON=".venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="$PYTHON3"
fi

# =========================
# Gestion des arguments
# =========================
while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-sonar) SKIP_SONAR=true; shift ;;
    --skip-pylint) SKIP_PYLINT=true; shift ;;
    *) shift ;;
  esac
done

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Vérification qualité OneAI (CI/CD compliant)${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# =========================
# Fonctions utilitaires
# =========================
run_check() {
    local name="$1"
    local cmd="$2"
    echo -e "${YELLOW}[${name}]${NC} Exécution..."
    if eval "$cmd"; then
        echo -e "${GREEN}✅ ${name} OK${NC}"
        echo "${name}: OK" >> "$SUMMARY"
    else
        echo -e "${RED}❌ ${name} ÉCHOUÉ${NC}"
        echo "${name}: FAILED" >> "$SUMMARY"
        return 1
    fi
}

auto_fix_style() {
    if [ -f "$SCRIPT_DIR/fix_style.sh" ]; then
        echo -e "${YELLOW}[0/8] Correction automatique du style (Black/Ruff/Isort)...${NC}"
        "$SCRIPT_DIR/fix_style.sh" 2>&1 | grep -E "(✅|✨|⚠️)" || true
        echo ""
    fi
}

# =========================
# Vérification complexité structure
# =========================
check_structure_complexity() {
    echo -e "${YELLOW}[Structure]${NC} Analyse de la complexité..."

    local score=10
    local issues=0

    > "$STRUCTURE_REPORT"
    echo "========================================" >> "$STRUCTURE_REPORT"
    echo "ANALYSE DE COMPLEXITÉ STRUCTURELLE" >> "$STRUCTURE_REPORT"
    echo "Date: $(date '+%Y-%m-%d %H:%M:%S')" >> "$STRUCTURE_REPORT"
    echo "Seuils: fichiers=$MAX_FILES_PER_DIR, sous-dossiers=$MAX_SUBDIRS_PER_DIR, profondeur=$MAX_DEPTH" >> "$STRUCTURE_REPORT"
    echo "========================================" >> "$STRUCTURE_REPORT"
    echo "" >> "$STRUCTURE_REPORT"

    for root_dir in "backend/app" "frontend" "backend/src" "tmp"; do
        if [ ! -d "$root_dir" ]; then
            continue
        fi

        echo "📂 Analyse de $root_dir" >> "$STRUCTURE_REPORT"
        echo "" >> "$STRUCTURE_REPORT"

        # 1. Profondeur max
        local max_depth_found=0
        while IFS= read -r dir; do
            local depth
            depth=$(echo "$dir" | tr -cd '/' | wc -c)
            if [ "$depth" -gt "$max_depth_found" ]; then
                max_depth_found=$depth
            fi
        done < <(find "$root_dir" -type d 2>/dev/null)

        local root_depth
        root_depth=$(echo "$root_dir" | tr -cd '/' | wc -c)
        local relative_depth=$((max_depth_found - root_depth))

        echo "   Profondeur max : $relative_depth (seuil: $MAX_DEPTH)" >> "$STRUCTURE_REPORT"
        if [ "$relative_depth" -gt "$MAX_DEPTH" ]; then
            echo "   ⚠️  Arborescence trop profonde" >> "$STRUCTURE_REPORT"
            score=$((score - 2))
            issues=$((issues + 1))
        else
            echo "   ✅ OK" >> "$STRUCTURE_REPORT"
        fi
        echo "" >> "$STRUCTURE_REPORT"

        # 2. Listing exhaustif fichiers par dossier
        echo "   Fichiers .py par dossier (seuil: $MAX_FILES_PER_DIR) :" >> "$STRUCTURE_REPORT"
        while IFS= read -r dir; do
            local file_count
            file_count=$(find "$dir" -maxdepth 1 -type f -name "*.py" 2>/dev/null | wc -l)
            if [ "$file_count" -gt "$MAX_FILES_PER_DIR" ]; then
                echo "      ❌ $dir : $file_count fichiers" >> "$STRUCTURE_REPORT"
                score=$((score - 1))
                issues=$((issues + 1))
            elif [ "$file_count" -gt 0 ]; then
                local status="✅"
                local warn_threshold=$(( MAX_FILES_PER_DIR * 80 / 100 ))
                if [ "$file_count" -ge "$warn_threshold" ]; then
                    status="⚠️ "
                fi
                echo "      $status $dir : $file_count fichiers" >> "$STRUCTURE_REPORT"
            fi
        done < <(find "$root_dir" -type d 2>/dev/null)
        echo "" >> "$STRUCTURE_REPORT"

        # 3. Listing exhaustif sous-dossiers par dossier
        echo "   Sous-dossiers par dossier (seuil: $MAX_SUBDIRS_PER_DIR) :" >> "$STRUCTURE_REPORT"
        while IFS= read -r dir; do
            local subdir_count
            subdir_count=$(find "$dir" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | wc -l)
            if [ "$subdir_count" -gt "$MAX_SUBDIRS_PER_DIR" ]; then
                echo "      ❌ $dir : $subdir_count sous-dossiers" >> "$STRUCTURE_REPORT"
                score=$((score - 1))
                issues=$((issues + 1))
            elif [ "$subdir_count" -gt 0 ]; then
                local status="✅"
                local warn_threshold=$(( MAX_SUBDIRS_PER_DIR * 80 / 100 ))
                if [ "$subdir_count" -ge "$warn_threshold" ]; then
                    status="⚠️ "
                fi
                echo "      $status $dir : $subdir_count sous-dossiers" >> "$STRUCTURE_REPORT"
            fi
        done < <(find "$root_dir" -type d 2>/dev/null)
        echo "" >> "$STRUCTURE_REPORT"
        echo "----------------------------------------" >> "$STRUCTURE_REPORT"
        echo "" >> "$STRUCTURE_REPORT"
    done

    if [ "$score" -lt 0 ]; then
        score=0
    fi

    echo "========================================" >> "$STRUCTURE_REPORT"
    echo "SCORE FINAL : $score/10" >> "$STRUCTURE_REPORT"
    echo "PROBLÈMES DÉTECTÉS : $issues" >> "$STRUCTURE_REPORT"
    echo "LÉGENDE : ✅ OK  ⚠️  Proche du seuil (>=80%)  ❌ Dépassement" >> "$STRUCTURE_REPORT"
    echo "========================================" >> "$STRUCTURE_REPORT"

    if [ "$issues" -eq 0 ]; then
        echo -e "${GREEN}✅ Structure OK (score: $score/10)${NC}"
        echo "Structure: OK ($score/10)" >> "$SUMMARY"
    else
        echo -e "${YELLOW}⚠️  Structure complexe (score: $score/10, $issues problèmes)${NC}"
        echo "   → Détails : $STRUCTURE_REPORT"
        echo "Structure: WARNINGS ($score/10, $issues issues)" >> "$SUMMARY"
    fi
}

# =========================
# Vérification code smell (taille fichiers)
# =========================
check_code_smell() {
    echo -e "${YELLOW}[Code Smell]${NC} Analyse de la taille des fichiers..."

    > "$CODE_SMELL_REPORT"
    echo "========================================" >> "$CODE_SMELL_REPORT"
    echo "ANALYSE CODE SMELL - TAILLE DES FICHIERS" >> "$CODE_SMELL_REPORT"
    echo "Date: $(date '+%Y-%m-%d %H:%M:%S')" >> "$CODE_SMELL_REPORT"
    echo "Seuil global: $MAX_LINES_PER_FILE lignes | Tolérance annotations: +10%" >> "$CODE_SMELL_REPORT"
    echo "========================================" >> "$CODE_SMELL_REPORT"
    echo "" >> "$CODE_SMELL_REPORT"

    PYTHONIOENCODING=utf-8 $PYTHON3 - <<PYEOF >> "$CODE_SMELL_REPORT"
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, ".")
from pathlib import Path

# Cherche le parser (depuis la racine projet ou depuis le répertoire du script)
_candidates = [
    "infrastructure/scripts/check_code_smell_parser.py",
    os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "check_code_smell_parser.py"),
]
_parser = next((p for p in _candidates if os.path.isfile(p)), None)
if _parser is None:
    raise FileNotFoundError("check_code_smell_parser.py introuvable")
exec(open(_parser, encoding="utf-8").read())

MAX_LINES = $MAX_LINES_PER_FILE
root_dirs = ["backend/app", "frontend"]

total_ok = 0
total_suppressed = 0
total_tolerance_warning = 0
total_tolerance_exceeded = 0
total_warning = 0
total_error = 0
total_files = 0

for root_dir in root_dirs:
    root = Path(root_dir)
    if not root.exists():
        continue

    print(f"📂 Analyse de {root_dir}")
    print()

    files = sorted(root.rglob("*.py"))
    for file_path in files:
        if "__pycache__" in str(file_path):
            continue

        try:
            line_count = sum(1 for _ in open(file_path, encoding="utf-8"))
        except OSError:
            continue

        result = evaluate_file(file_path, line_count, MAX_LINES)
        status = result["status"]
        rel_path = file_path.relative_to(Path("."))

        print(f"      {result['message']}")
        print(f"         → {rel_path}")

        total_files += 1

        if status == "ok":
            total_ok += 1
        elif status == "suppressed":
            total_suppressed += 1
        elif status == "tolerance_warning":
            total_tolerance_warning += 1
        elif status == "tolerance_exceeded":
            total_tolerance_exceeded += 1
        elif status == "warning":
            total_warning += 1
        elif status == "error":
            total_error += 1

    print()
    print("----------------------------------------")
    print()

# ✅ Score basé sur le taux de succès avec float
total_issues = total_error + total_tolerance_exceeded
score = round(10 * (1 - total_issues / total_files), 2) if total_files else 10.0
score = max(0.0, score)

print("========================================")
print(f"SCORE FINAL : {score:.2f}/10")
print(f"📁 Total fichiers analysés : {total_files}")
print(f"✅ OK                    : {total_ok}")
print(f"🟠 Supprimés (annotés)   : {total_suppressed}")
print(f"⚠️  Tolérance warning    : {total_tolerance_warning}")
print(f"❌ Tolérance dépassée    : {total_tolerance_exceeded}")
print(f"⚠️  Warning global       : {total_warning}")
print(f"❌ Dépassement global    : {total_error}")
print("LÉGENDE :")
print("  ✅ OK = dans les clous naturellement")
print("  🟠 Supprimé = dans les clous via annotation")
print("  ⚠️  Tolérance = annotation dépassée mais dans les 10%")
print("  ❌ = action requise")
print("========================================")

# ✅ Écriture du score en float
import os
_score_file = os.path.join("$ARTIFACT_DIR", "code_smell_score.txt")
with open(_score_file, "w", encoding="utf-8") as f:
    f.write(f"{score:.2f}\n{total_issues}")
PYEOF

    if [ -f "$ARTIFACT_DIR/code_smell_score.txt" ]; then
        SMELL_SCORE=$(sed -n '1p' "$ARTIFACT_DIR/code_smell_score.txt")
        SMELL_ISSUES=$(sed -n '2p' "$ARTIFACT_DIR/code_smell_score.txt")
        rm -f "$ARTIFACT_DIR/code_smell_score.txt"
    else
        SMELL_SCORE=0.00
        SMELL_ISSUES=99
    fi

    # ✅ Logique de couleurs intelligente avec comparaison float
    if [ "$SMELL_ISSUES" -eq 0 ]; then
        echo -e "${GREEN}✅ Code Smell OK (score: $SMELL_SCORE/10)${NC}"
        echo "Code Smell: OK ($SMELL_SCORE/10)" >> "$SUMMARY"
    elif $PYTHON3 -c "exit(0 if float('$SMELL_SCORE') >= 8.0 else 1)"; then
        echo -e "${YELLOW}⚠️  Code Smell : $SMELL_ISSUES problème(s) (score: $SMELL_SCORE/10)${NC}"
        echo "   → Bon score mais problèmes à corriger"
        echo "   → Détails : $CODE_SMELL_REPORT"
        echo "Code Smell: WARNINGS ($SMELL_SCORE/10, $SMELL_ISSUES issues)" >> "$SUMMARY"
    else
        echo -e "${RED}❌ Code Smell : $SMELL_ISSUES problème(s) (score: $SMELL_SCORE/10)${NC}"
        echo "   → Score faible, action requise"
        echo "   → Détails : $CODE_SMELL_REPORT"
        echo "Code Smell: FAILED ($SMELL_SCORE/10, $SMELL_ISSUES issues)" >> "$SUMMARY"
    fi
}

# =========================
# 1. Nettoyage
# =========================
run_check "Nettoyage" \
"find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null;
 find . -name '*.pyc' -delete 2>/dev/null"

# =========================
# 2. Auto-fix style
# =========================
auto_fix_style

# =========================
# 3. Vérification structure
# =========================
check_structure_complexity

# =========================
# 4. Vérification code smell
# =========================
_smell_key="smell_$(cache_key backend/app frontend)"
if _smell_cached=$(cache_get "$_smell_key"); then
    echo -e "${YELLOW}[Code Smell]${NC} (cache) ${_smell_cached}"
    echo "Code Smell: ${_smell_cached}" >> "$SUMMARY"
else
    check_code_smell
    _smell_result="OK (${SMELL_SCORE:-10.00}/10)"
    [ "${SMELL_ISSUES:-0}" -gt 0 ] && _smell_result="WARNINGS (${SMELL_SCORE}/10, ${SMELL_ISSUES} issues)"
    cache_set "$_smell_key" "$_smell_result"
fi

# =========================
# 4b. Requirements — imports
# =========================
_req_key="req_$(cache_key backend/app frontend backend/src)_$(md5sum requirements/*.txt 2>/dev/null | md5sum | cut -c1-8)"
if _req_cached=$(cache_get "$_req_key"); then
    echo -e "${YELLOW}[Requirements]${NC} (cache) ${_req_cached}"
    echo "Requirements: ${_req_cached}" >> "$SUMMARY"
else
    echo -e "${YELLOW}[Requirements]${NC} Vérification des imports..."
    if bash "$SCRIPT_DIR/check_requirements.sh" 2>&1; then
        _req_unused=$(cat "$ARTIFACT_DIR/requirements_score.txt" 2>/dev/null || echo "0")
        if [ "$_req_unused" -eq 0 ]; then
            cache_set "$_req_key" "OK"
            echo "Requirements: OK" >> "$SUMMARY"
        else
            cache_set "$_req_key" "WARNINGS (${_req_unused} package(s) sans import)"
            echo "Requirements: WARNINGS (${_req_unused} package(s) sans import)" >> "$SUMMARY"
        fi
    else
        echo "Requirements: ERREUR (script échoué)" >> "$SUMMARY"
    fi
fi

# =========================
# 5. Ruff
# =========================
if command -v ruff &> /dev/null; then
    _ruff_key="ruff_$(cache_key backend/app frontend)"
    if _ruff_cached=$(cache_get "$_ruff_key"); then
        echo -e "${YELLOW}[Ruff]${NC} (cache) ${_ruff_cached}"
        echo "Ruff: ${_ruff_cached}" >> "$SUMMARY"
    else
    echo -e "${YELLOW}[Ruff]${NC} Analyse (backend/app + frontend)..."
    ruff check backend/app/ frontend/ --output-format=full > "$RUFF_REPORT" || true

    RUFF_ERRORS=$(grep -E "^(backend/app|frontend)" "$RUFF_REPORT" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$RUFF_ERRORS" -gt 0 ]; then
        echo -e "${YELLOW}📄 Ruff – problèmes restants (extrait) :${NC}"
        head -50 "$RUFF_REPORT"
        echo ""
        echo -e "${YELLOW}📊 Décompte des erreurs par zone :${NC}"
        echo "  • Backend  : $(grep '^backend/app' "$RUFF_REPORT" | wc -l) erreurs"
        echo "  • Frontend : $(grep '^frontend' "$RUFF_REPORT" | wc -l) erreurs"
        echo "→ Rapport complet : $RUFF_REPORT"
        cache_set "$_ruff_key" "WARNINGS ($RUFF_ERRORS erreurs)"
        echo "Ruff: WARNINGS ($RUFF_ERRORS erreurs)" >> "$SUMMARY"
    else
        echo -e "${GREEN}✅ Ruff clean${NC}"
        cache_set "$_ruff_key" "OK"
        echo "Ruff: OK" >> "$SUMMARY"
    fi
    fi  # fin bloc cache Ruff
else
    echo -e "${YELLOW}⚠️ Ruff non installé${NC}"
fi

# =========================
# 6. Pylint
# =========================
if [ "$SKIP_PYLINT" = false ]; then
    # Utiliser python -m pylint pour éviter les problèmes de shebang Windows/WSL
    if $VENV_PYTHON -m pylint --version &>/dev/null 2>&1; then
        PYLINT_CMD="$VENV_PYTHON -m pylint"
    elif python -m pylint --version &>/dev/null 2>&1; then
        PYLINT_CMD="python -m pylint"
    else
        PYLINT_CMD=""
    fi

    if [ -n "$PYLINT_CMD" ]; then

        # ── Pylint FE ──
        _fe_key="pylint_fe_$(cache_key frontend)"
        if FE_SCORE=$(cache_get "$_fe_key"); then
            echo -e "${YELLOW}[Pylint FE]${NC} (cache) Score : ${FE_SCORE}/10"
        else
            echo -e "${YELLOW}[Pylint FE]${NC} Vérification frontend..."
            $PYLINT_CMD frontend/ --rcfile=pyproject.toml > "$PYLINT_FE_LOG" 2>&1 || true
            FE_SCORE=$($PYTHON3 - <<EOF
import re
log=open("$PYLINT_FE_LOG").read()
m=re.search(r"rated at ([0-9.]+)/10", log)
print(m.group(1) if m else "0.0")
EOF
)
            cache_set "$_fe_key" "$FE_SCORE"
            echo -e "${YELLOW}📊 Score Pylint FE : ${FE_SCORE}/10${NC}"
        fi
        echo "Pylint FE: ${FE_SCORE}/10" >> "$SUMMARY"
        $PYTHON3 -c "exit(0 if float('$FE_SCORE') >= 7 else 1)" || { tail -20 "$PYLINT_FE_LOG"; exit 1; }

        # ── Pylint BE ──
        _be_key="pylint_be_$(cache_key backend/app)"
        if BE_SCORE=$(cache_get "$_be_key"); then
            echo -e "${YELLOW}[Pylint BE]${NC} (cache) Score : ${BE_SCORE}/10"
        else
            echo -e "${YELLOW}[Pylint BE]${NC} Vérification backend..."
            $PYLINT_CMD backend/app --rcfile=pyproject.toml > "$PYLINT_BE_LOG" 2>&1 || true
            BE_SCORE=$($PYTHON3 - <<EOF
import re
log=open("$PYLINT_BE_LOG").read()
m=re.search(r"rated at ([0-9.]+)/10", log)
print(m.group(1) if m else "0.0")
EOF
)
            cache_set "$_be_key" "$BE_SCORE"
            echo -e "${YELLOW}📊 Score Pylint BE : ${BE_SCORE}/10${NC}"
        fi
        echo "Pylint BE: ${BE_SCORE}/10" >> "$SUMMARY"
        $PYTHON3 -c "exit(0 if float('$BE_SCORE') >= 7 else 1)" || { tail -20 "$PYLINT_BE_LOG"; exit 1; }

    else
        echo -e "${RED}❌ Pylint non installé (ni dans .venv ni dans PATH)${NC}"

        exit 1
    fi
else
    echo -e "${YELLOW}⚠️ Pylint ignoré (--skip-pylint)${NC}"
    echo "Pylint: SKIPPED" >> "$SUMMARY"
fi

# =========================
# 7. Tests + couverture
# =========================
# Préférer le Python du venv pour éviter les problèmes de shebang Windows
VENV_PYTHON=".venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="$PYTHON3"
fi

if $VENV_PYTHON -m pytest --version &>/dev/null; then
    # Cache : hash des tests ET du code testé
    _test_key="tests_$(cache_key backend/tests backend/app)"
    if _test_cached=$(cache_get "$_test_key"); then
        echo -e "${YELLOW}[Tests]${NC} (cache) ${_test_cached}"
        echo "Tests: ${_test_cached}" >> "$SUMMARY"
    else
        echo -e "${YELLOW}[Tests]${NC} Exécution pytest..."
        if $VENV_PYTHON -m pytest backend/tests \
            --cov=backend/app \
            --cov-report=xml:backend/coverage.xml \
            --cov-fail-under=$COVERAGE_THRESHOLD -q > "$PYTEST_LOG" 2>&1; then

            echo -e "${GREEN}✅ Tests OK${NC}"
            cache_set "$_test_key" "OK (coverage ≥ ${COVERAGE_THRESHOLD}%)"
            echo "Tests: OK (coverage ≥ ${COVERAGE_THRESHOLD}%)" >> "$SUMMARY"
        else
            echo -e "${RED}❌ Tests échoués${NC}"
            echo -e "${YELLOW}📄 Dernières erreurs pytest :${NC}"
            tail -40 "$PYTEST_LOG"
            echo "→ Log complet : $PYTEST_LOG"
            echo "Tests: FAILED" >> "$SUMMARY"
            exit 1
        fi
    fi
else
    echo -e "${RED}❌ Pytest non installé (ni dans .venv ni dans PATH)${NC}"
    exit 1
fi

# =========================
# Résumé final
# =========================
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✅ Vérification terminée${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}📄 Résumé qualité :${NC}"
cat "$SUMMARY"
echo ""
echo -e "${GREEN}📂 Artefacts disponibles dans ${ARTIFACT_DIR}${NC}"
echo -e "${GREEN}   • Structure  : ${ARTIFACT_DIR}/structure_complexity.txt${NC}"
echo -e "${GREEN}   • Code Smell : ${ARTIFACT_DIR}/code_smell.txt${NC}"
echo -e "${GREEN}🚀 Prêt à push !${NC}"