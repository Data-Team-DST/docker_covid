#!/bin/bash
# fix_style.sh - Correction automatique du style Python
set -e
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

TARGETS="backend/app frontend src"

echo -e "${YELLOW}🎨 Correction automatique du style Python...${NC}"
echo ""

if ! command -v black &> /dev/null; then
    echo -e "${YELLOW}⚠️  Black non installé → pip install black${NC}"
    exit 1
fi

# 1. Black : formatage principal
echo -e "${YELLOW}➡️  Black : formatage code...${NC}"
black $TARGETS --line-length 79 --target-version py312 2>&1 \
    | grep -E "(reformatted|unchanged|error)" || true
echo -e "${GREEN}✅ Black terminé${NC}"

# 2. Isort : tri des imports (seul maître)
echo -e "${YELLOW}➡️  Isort : tri des imports...${NC}"
isort $TARGETS \
    --settings-path pyproject.toml \
    --line-length 79 2>&1 \
    | grep -E "(Fixing|Skipped|error)" || true
echo -e "${GREEN}✅ Isort terminé${NC}"

# 3. Ruff : erreurs logiques SANS AUCUN CODE IMPORT
# ⚠️ On exclut explicitement F4xx (imports) et I (isort)
echo -e "${YELLOW}➡️  Ruff : correction erreurs (SANS imports)...${NC}"
ruff check $TARGETS --fix \
    --select E,W,B,C4,UP \
    --ignore F401,F403,F405 2>&1 \
    | grep -E "(fixed|unchanged|error|Found)" || true
echo -e "${GREEN}✅ Ruff terminé${NC}"

echo ""
echo -e "${GREEN}✨ Correction automatique terminée !${NC}"
echo -e "${YELLOW}💡 Conseil : Relancez './check_quality.sh' pour vérifier${NC}"