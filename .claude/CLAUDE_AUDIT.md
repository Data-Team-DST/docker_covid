# CLAUDE AUDIT MODE — docker_covid

## Objectif
Analyser le repo sans le modifier. Toujours commencer par ce mode avant un "nettoyage" —
surtout si la soutenance est proche (voir CLAUDE.md § Calendrier).

## Vérifications

### Fuite / exposition (repo public)
- Fichiers trackés contenant secrets, clés API, mots de passe, données personnelles
- `.env`, `.claude/`, `mlruns/`, `data/raw/` correctement gitignorés
- Résidus de notebooks (`test.ipynb`, `train.ipynb`, `train_segmentation.ipynb`) : sorties de
  cellules contenant des chemins locaux, tokens, ou données sensibles avant tout commit

### Architecture
- Couplage entre backend/, data-service/, log-service/ (imports Python directs interdits)
- Cohérence des ports déclarés (README vs config.py vs docker-compose.yml)
- Duplication entre `shared/logging_config.py` et les copies locales éventuelles

### Qualité de code
- Fonctions/fichiers hors gabarit (voir `.claude/rules/common/coding-style.md`)
- Tests manquants sur les modules critiques (`app/models/loader.py`, `app/features/preprocessing.py`)
- Scripts orphelins non wirés au Makefile

### CI/CD
- `.github/workflows/cicd.yml` : permissions au niveau job (pas workflow), versions pip pinnées,
  actions tierces sur SHA — voir `.claude/rules/common/github-actions-security.md`

## Sortie
- Findings classés par sévérité
- Explications claires
- Suggestions uniquement (aucune modification sans validation explicite)
