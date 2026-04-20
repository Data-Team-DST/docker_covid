#!/bin/bash
# check_quality.sh - Vérification qualité alignée CI/CD Sanofi
# Usage: ./check_quality.sh [--skip-sonar] [--skip-pylint]

set -e

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
mkdir -p "$ARTIFACT_DIR"

RUFF_REPORT="$ARTIFACT_DIR/ruff.txt"
PYLINT_FE_LOG="$ARTIFACT_DIR/pylint_fe.log"
PYLINT_BE_LOG="$ARTIFACT_DIR/pylint_be.log"
PYTEST_LOG="$ARTIFACT_DIR/pytest.log"
STRUCTURE_REPORT="$ARTIFACT_DIR/structure_complexity.txt"
CODE_SMELL_REPORT="$ARTIFACT_DIR/code_smell.txt"
SUMMARY="$ARTIFACT_DIR/summary.txt"

> "$SUMMARY"

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
    if [ -f "fix_style.sh" ]; then
        echo -e "${YELLOW}[0/8] Correction automatique du style (Black/Ruff/Isort)...${NC}"
        ./fix_style.sh 2>&1 | grep -E "(✅|✨|⚠️)" || true
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

    for root_dir in "backend/app" "frontend" "src" "tmp"; do
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

    python3 - <<PYEOF >> "$CODE_SMELL_REPORT"
import sys
sys.path.insert(0, ".")
from pathlib import Path

exec(open("check_code_smell_parser.py").read())

MAX_LINES = $MAX_LINES_PER_FILE
root_dirs = ["backend/app", "frontend", "tmp"]

total_ok = 0
total_suppressed = 0
total_tolerance_warning = 0
total_tolerance_exceeded = 0
total_warning = 0
total_error = 0
total_files = 0

for root_dir in root_dirs + ["tmp"]:
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
with open("/tmp/code_smell_score.txt", "w") as f:
    f.write(f"{score:.2f}\n{total_issues}")
PYEOF

    if [ -f "/tmp/code_smell_score.txt" ]; then
        SMELL_SCORE=$(sed -n '1p' /tmp/code_smell_score.txt)
        SMELL_ISSUES=$(sed -n '2p' /tmp/code_smell_score.txt)
        rm -f /tmp/code_smell_score.txt
    else
        SMELL_SCORE=0.00
        SMELL_ISSUES=99
    fi

    # ✅ Logique de couleurs intelligente avec comparaison float
    if [ "$SMELL_ISSUES" -eq 0 ]; then
        echo -e "${GREEN}✅ Code Smell OK (score: $SMELL_SCORE/10)${NC}"
        echo "Code Smell: OK ($SMELL_SCORE/10)" >> "$SUMMARY"
    elif python3 -c "exit(0 if float('$SMELL_SCORE') >= 8.0 else 1)"; then
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
check_code_smell

# =========================
# 5. Ruff
# =========================
if command -v ruff &> /dev/null; then
    echo -e "${YELLOW}[Ruff]${NC} Analyse (backend + frontend + tmp)..."
    ruff check . --output-format=full > "$RUFF_REPORT" || true

    if [ -s "$RUFF_REPORT" ]; then
        echo -e "${YELLOW}📄 Ruff – problèmes restants (extrait) :${NC}"
        head -50 "$RUFF_REPORT"
        echo ""
        echo -e "${YELLOW}📊 Décompte des erreurs par zone :${NC}"
        echo "  • Backend  : $(grep '^backend/app' "$RUFF_REPORT" | wc -l) erreurs"
        echo "  • Frontend : $(grep '^frontend' "$RUFF_REPORT" | wc -l) erreurs"
        echo "  • Tmp      : $(grep '^tmp/' "$RUFF_REPORT" | wc -l) erreurs"
        echo "→ Rapport complet : $RUFF_REPORT"
        echo "Ruff: WARNINGS" >> "$SUMMARY"
    else
        echo -e "${GREEN}✅ Ruff clean${NC}"
        echo "Ruff: OK" >> "$SUMMARY"
    fi
else
    echo -e "${YELLOW}⚠️ Ruff non installé${NC}"
fi

# =========================
# 6. Pylint
# =========================
if [ "$SKIP_PYLINT" = false ]; then
    if command -v pylint &> /dev/null; then

        echo -e "${YELLOW}[Pylint FE]${NC} Vérification frontend..."
        pylint frontend/ --ignore=page > "$PYLINT_FE_LOG" 2>&1 || true

        FE_SCORE=$(python3 - <<EOF
import re
log=open("$PYLINT_FE_LOG").read()
m=re.search(r"rated at ([0-9.]+)/10", log)
print(m.group(1) if m else "0.0")
EOF
)
        echo -e "${YELLOW}📊 Score Pylint FE : ${FE_SCORE}/10${NC}"
        echo "Pylint FE: ${FE_SCORE}/10" >> "$SUMMARY"

        python3 - <<EOF
if float("$FE_SCORE") < 7:
    exit(1)
EOF
        if [ $? -ne 0 ]; then
            tail -20 "$PYLINT_FE_LOG"
            exit 1
        fi

        echo -e "${YELLOW}[Pylint BE]${NC} Vérification backend..."
        pylint backend/app > "$PYLINT_BE_LOG" 2>&1 || true

        BE_SCORE=$(python3 - <<EOF
import re
log=open("$PYLINT_BE_LOG").read()
m=re.search(r"rated at ([0-9.]+)/10", log)
print(m.group(1) if m else "0.0")
EOF
)
        echo -e "${YELLOW}📊 Score Pylint BE : ${BE_SCORE}/10${NC}"
        echo "Pylint BE: ${BE_SCORE}/10" >> "$SUMMARY"

        python3 - <<EOF
if float("$BE_SCORE") < 7:
    exit(1)
EOF
        if [ $? -ne 0 ]; then
            tail -20 "$PYLINT_BE_LOG"
            exit 1
        fi

    else
        echo -e "${RED}❌ Pylint non installé${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️ Pylint ignoré (--skip-pylint)${NC}"
    echo "Pylint: SKIPPED" >> "$SUMMARY"
fi

# =========================
# 7. Tests + couverture
# =========================
if command -v pytest &> /dev/null; then
    echo -e "${YELLOW}[Tests]${NC} Exécution pytest..."
    if pytest backend/tests \
        --cov=backend/app \
        --cov-report=xml:backend/coverage.xml \
        --cov-fail-under=$COVERAGE_THRESHOLD -q > "$PYTEST_LOG" 2>&1; then

        echo -e "${GREEN}✅ Tests OK${NC}"
        echo "Tests: OK (coverage ≥ ${COVERAGE_THRESHOLD}%)" >> "$SUMMARY"

    else
        echo -e "${RED}❌ Tests échoués${NC}"
        echo -e "${YELLOW}📄 Dernières erreurs pytest :${NC}"
        tail -40 "$PYTEST_LOG"
        echo "→ Log complet : $PYTEST_LOG"
        echo "Tests: FAILED" >> "$SUMMARY"
        exit 1
    fi
else
    echo -e "${RED}❌ Pytest non installé${NC}"
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