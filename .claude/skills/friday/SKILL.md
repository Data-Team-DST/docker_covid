---
name: friday
description: Rituel vendredi 14h — inventaire qualité, sécurité, dette, docs. Mesurer et prioriser, jamais corriger dans la foulée. Génère un rapport daté dans docs/friday-audits/.
origin: project
---

# /friday — Rituel vendredi 14h

Inventaire hebdomadaire du repo courant. Philosophie unique :
**mesurer et prioriser, pas corriger**. Tout finding devient une ligne dans le
rapport avec une estimation en heures. Le lundi tu ouvres le rapport, tu planifies.

## Déclencheur

`/friday` — à lancer chaque vendredi vers 14h, avant de fermer le laptop.

## Philosophie

- Mesurer d'abord, agir ensuite (jamais corriger dans la session du vendredi)
- Chaque finding → ligne dans le rapport avec P1/P2/P3 et estimation heures
- Le rapport est daté (`YYYY-MM-DD_HHhMM.md`) pour permettre un historique
- Durée cible : 45-60 min (75-80 min les vendredis avec Phase 7 mensuelle).
  Si ça dépasse, couper à Phase 4 et skipper les docs

---

## Séquence d'exécution

### Phase 0 — Vérifier si l'audit mensuel est dû (~1 min)

```bash
# Dernier rapport friday contenant une section "## Audit mensuel"
grep -l "## Audit mensuel" docs/friday-audits/*.md 2>/dev/null | sort | tail -1
```

- Aucun fichier trouvé → l'audit mensuel n'a jamais tourné, le déclencher cette
  fois (aller en Phase 7 en fin de rituel).
- Fichier trouvé → comparer sa date (nom de fichier `YYYY-MM-DD_HHhMM.md`) à
  aujourd'hui. Si ≥ 30 jours → déclencher Phase 7. Sinon → passer Phase 7.

### Phase 1 — Snapshot technique (Bash, ~10 min)

Lancer en parallèle :

```bash
# Qualité globale — les vrais chiffres de la semaine
make quality

# Activité de la semaine
git log --oneline --since="last monday" --name-only

# État du repo
git status --short
git stash list

# État DVC
source mlflow-env/bin/activate && dvc status
```

Collecter : score lint par service, coverage par service, nombre de commits,
liste des fichiers touchés, stash oubliés, delta DVC non pushé.

---

### Phase 2 — Choix repo-scan / production-audit (~5 min)

Analyser la liste des fichiers touchés cette semaine (Phase 1) avec la règle :

| Fichiers touchés cette semaine | Action |
|---|---|
| Code métier uniquement (`src/`, `tests/`) | `/repo-scan` seulement |
| Infra touchée (voir liste ci-dessous) | `/repo-scan` **ET** `/production-audit` |
| Semaine légère (<5 fichiers, aucune infra) | Passer directement à Phase 3 |

**Fichiers infra qui déclenchent `/production-audit` en plus** :
- `.github/workflows/` (CI/CD)
- `Dockerfile*`, `docker-compose*`, `ml-base/`
- `kubernetes/` (ou équivalent manifests de déploiement)
- `Makefile` (targets déploiement)
- `.env.example`, `pyproject.toml` (dépendances majeures)
- `sonar-project.properties`

Appeler les skills appropriés et collecter leurs outputs.

---

### Phase 3 — Sécurité (~10 min)

Lancer `/security-scan` (scan config Claude `.claude/`).

En complément, vérifier rapidement dans le code touché cette semaine :
- Absence de `verify=False` dans les nouveaux appels requests
- Absence de secrets hardcodés
- CORS credentials cohérents (règle SonarQube `web:S5122`)

**Revue CVE image de base (cadence ~2 semaines, pas chaque vendredi)** —
`docs/security/base-image-cve-review.md` tient un tableau « Historique des
revues ». Comparer la date de la dernière ligne à aujourd'hui :

- **< 14 jours** → passer, rien à faire.
- **≥ 14 jours** → relancer le scan et mettre à jour le tableau :

```bash
MSYS_NO_PATHCONV=1 docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy:latest image --severity CRITICAL,HIGH --format table python:3.12-slim
```

Comparer au relevé précédent dans le fichier, puis :
1. **Le code applicatif touché depuis la dernière revue invoque-t-il désormais
   un des paquets à risque** (perl, gzip, mount, ncurses, libacl) — nouveau
   `subprocess`, nouvelle dépendance qui shell-out ? Si oui → **P1**, la
   surface d'exploitation n'est plus 0, retriager immédiatement (ne pas
   attendre la planification du lundi).
2. **Une des CVE `affected`/`fix_deferred` a-t-elle un correctif désormais ?**
   Si oui → **P3** "rebuild recommandé pour absorber le correctif".
3. Ajouter une ligne au tableau « Historique des revues » du fichier
   (date, total CVE, réponse à la question 1, action). Ne pas corriger le
   Dockerfile dans la foulée (philosophie `/friday` : mesurer, pas corriger) —
   juste consigner et faire remonter en section Sécurité du rapport si P1.

---

### Phase 3b — Sécurité agentic (~5 min)

En complément du `/security-scan`, vérifier le harness Claude Code :

```bash
# Hooks avec commandes outbound ou override de base URL
grep -rn "ANTHROPIC_BASE_URL\|enableAllProjectMcpServers" .claude/hooks/ .claude/settings*.json 2>/dev/null
grep -rn "curl\|wget\|nc \|scp \|ssh " .claude/hooks/ 2>/dev/null

# Unicode caché dans skills / rules / agents
rg -nP '[\x{200B}\x{200C}\x{200D}\x{2060}\x{FEFF}\x{202A}-\x{202E}]' .claude/ 2>/dev/null

# Secrets dans les fichiers mémoire
grep -rn "password\|api_key\|token\|secret" .claude/memory/ 2>/dev/null | grep -v "example\|placeholder\|#"

# MCP servers actifs
python3 -c "import json,pathlib; p=pathlib.Path('.mcp.json'); print(list(json.loads(p.read_text()).get('mcpServers',{}).keys())) if p.exists() else print('no .mcp.json')" 2>/dev/null
```

Signaler dans le rapport (section Sécurité) :
- Tout hook avec commande outbound → **P1**
- `ANTHROPIC_BASE_URL` override détecté → **P1**
- MCP server non documenté dans le rapport précédent → **P2**
- Secret dans les fichiers mémoire → **P1**
- Unicode caché dans les fichiers de contexte → **P1**

---

### Phase 4 — Dette & code mort (~10 min)

Lancer `/refactor-clean` ou `/prune` en ciblant les services modifiés cette semaine.

Si aucun service n'a été modifié (semaine de docs/infra), passer cette phase.

Collecter : fonctions mortes, imports inutilisés, complexité cognitive > 15
(règle SonarQube `python:S3776`), docstrings manquantes.

**Check complexité cyclomatique dédié** (couvert indirectement par
`/refactor-clean`, ce qui laisse passer les fonctions proches du seuil sans
relecture manuelle dédiée). Scope uniquement les `.py` touchés cette semaine
(liste de la Phase 1) — pas la peine de rescanner un fichier non modifié :

```bash
# radon doit être installé dans le venv du service concerné (pip install radon)
FILES=$(git log --oneline --since="last monday" --name-only --pretty=format: \
  | sort -u | grep -E '\.py$')
for f in $FILES; do
  [ -f "$f" ] || continue
  radon cc "$f" -s -n C 2>/dev/null  # -n C = n'affiche que CC ≥ 11 (C/D/E/F)
done
```

Toute fonction en C (11-15, sous le seuil SonarQube 15 mais proche) → noter
en P3 "à surveiller". Toute fonction D+ (>15) → P2, violation de la règle
`python:S3776`.

**Check disables d'outil qualité non justifiés**. Scope tout le repo (pas
juste la semaine — un disable existant sans trace reste un problème même
s'il n'a pas été touché récemment) :

```bash
grep -rn "pylint: disable\|noqa:\|# NOSONAR\|type: ignore" --include="*.py" . 2>/dev/null
```

Pour chaque résultat : la ligne au-dessus ou la même ligne doit contenir une
justification en langage naturel (pas juste le disable seul). Si absente →
P2 "disable non tracé — soit justifier, soit corriger le vrai problème plutôt
que faire taire l'outil". Ne jamais retirer un disable soi-même pendant
`/friday` — mesurer, signaler, laisser l'utilisateur trancher.

**Check dérive des commentaires** : lancer l'agent `comment-analyzer` sur les
fichiers modifiés cette semaine (liste de la Phase 1) pour détecter les
commentaires devenus inexacts ou obsolètes par rapport au code qu'ils
accompagnent (pas seulement l'absence de docstring, déjà couverte
ci-dessus — ici on vérifie que ce qui est écrit est encore vrai). Si aucun
fichier `.py` n'a été modifié cette semaine, passer ce check.

**Check nommage — à intégrer systématiquement en Phase 4** :

```bash
# 1. Fichiers dépassant leur limite par type
python3 - <<'EOF'
from pathlib import Path
LIMITS = {"_router.py": 300, "_service.py": 200, "_utils.py": 200, "_helpers.py": 200, "main.py": 50}
for path in Path(".").rglob("*.py"):
    if any(p in str(path) for p in [".venv", "ml-env", "mlflow-env", "__pycache__"]):
        continue
    n = sum(1 for _ in path.open())
    for suffix, limit in LIMITS.items():
        if path.name.endswith(suffix) and n > limit:
            print(f"OVER LIMIT ({n}/{limit}): {path}")
EOF

# 2. Routers avec logique métier privée (signal de responsabilité mixte)
grep -rn "^def _\|^async def _" --include="*_router.py" backend/ data-service/ log-service/ dashboard/ 2>/dev/null
```

Signaler dans le rapport tout fichier **hors limite** ou **router contenant des helpers privés**
avec priorité P2 et estimation de refacto.

---

### Phase 5 — Docs & codemaps (~10 min)

Lancer dans l'ordre :
1. `/update-codemaps` — met à jour `docs/CODEMAPS/`
2. `/update-docs` — met à jour les READMEs et guides

Si la semaine n'a pas touché d'API ni d'architecture, passer rapidement.

---

### Phase 6 — Rapport (générer le fichier, ~10 min)

Créer le fichier `docs/friday-audits/YYYY-MM-DD_HHhMM.md` avec la date et
l'heure réelles au moment de la rédaction (format : `2026-05-22_14h35`).

Structure obligatoire du rapport :

```markdown
# Audit vendredi YYYY-MM-DD HHhMM

## Métriques semaine

| Métrique | Valeur | Δ vs semaine précédente |
|----------|--------|------------------------|
| Lint moyen | X.X/10 | — |
| Coverage backend | X% | — |
| Coverage data-service | X% | — |
| Commits semaine | N | — |
| Fichiers touchés | N | — |

## Activité semaine
<!-- Résumé des commits : quoi a bougé, dans quel service -->

## Findings

### Sécurité
<!-- Issues trouvées par /security-scan + vérifications manuelles -->
<!-- "RAS" si rien à signaler -->

### Architecture & production-readiness
<!-- Issues /repo-scan + /production-audit si lancé -->
<!-- "RAS" si rien à signaler -->

### Dette technique
<!-- Issues /refactor-clean — complexité, code mort, docstrings -->
<!-- "RAS" si rien à signaler -->

### DVC & données
<!-- Delta DVC non pushé, fichiers orphelins, cohérence extraction_status.json -->
<!-- "RAS" si rien à signaler -->

<!-- Section suivante uniquement si Phase 0 a déclenché la Phase 7 ce vendredi -->
## Audit mensuel
<!-- Résultats skill-comply / skill-stocktake / rules-distill / eval-harness, voir Phase 7 -->

## Actions prioritisées

| # | Action | Service | P | Estimation | À planifier |
|---|--------|---------|---|-----------|-------------|
| 1 | ... | backend | P1 | 2h | Semaine N+1 |
| 2 | ... | data-service | P2 | 4h | Semaine N+1 |
| 3 | ... | tous | P3 | 1j | Backlog |

**Légende priorité** : P1 = bloquant ou sécurité · P2 = qualité importante · P3 = amélioration

## Bilan

<!-- Une phrase : ce qui a bien marché cette semaine, ce qui mérite attention la semaine prochaine -->
```

---

### Phase 7 — Audit mensuel (conditionnel, seulement si Phase 0 l'a déclenché, ~20 min)

Cette phase ne tourne qu'une fois par mois environ (voir Phase 0) — elle
exerce des outils qui coûtent plus cher (tokens, temps) que le rituel
hebdomadaire habituel, pour détecter une dérive que Phase 1-6 ne voient pas :
est-ce que Claude suit vraiment les règles du projet, et les skills/commandes
installées sont-elles toujours pertinentes.

Lancer dans l'ordre, en acceptant les échecs partiels (chaque outil est
indépendant, un échec n'empêche pas les autres) :

1. **`skill-comply`** sur 2-3 règles critiques du projet — privilégier celles
   qui protègent contre un risque réel (ex. `.claude/rules/common/security.md`,
   ou une règle du contrat comportemental de `CLAUDE.md`). Vérifie
   empiriquement que Claude suit vraiment la règle, pas seulement qu'elle est
   écrite.
2. **`skill-stocktake`** (mode Quick Scan) sur `.claude/skills/` et
   `.claude/commands/` — repère les skills tombées en désuétude ou cassées.
3. **`rules-distill`** — seulement si `skill-stocktake` (étape précédente) a
   révélé un pattern récurrent qui mériterait de devenir une règle dans
   `.claude/rules/` ; sinon passer, ce skill n'a d'intérêt qu'en suite directe
   de `skill-stocktake`.
4. **`eval-harness`** — seulement si un besoin d'évaluation formalisée est
   apparu depuis le dernier audit mensuel (nouveau prompt, changement de
   modèle, etc.) ; sinon noter "rien à évaluer ce mois-ci".

Ajouter la section `## Audit mensuel` dans le rapport avec les résultats des
4 (ou "RAS" si rien d'anormal trouvé). C'est cette section que Phase 0
cherche le vendredi suivant pour savoir si le prochain audit mensuel est dû.

---

## Ce que ce skill ne fait PAS

- Il n'applique aucun correctif — il observe et consigne
- Il ne commit pas le rapport automatiquement (vous décidez)
- Il ne lance pas `make friday` dans le Makefile (les checks Bash sont embarqués ici)

## Anti-patterns à éviter

- Corriger un bug trouvé pendant l'audit dans la même session
- Skipper Phase 3 (sécurité) sous prétexte que "rien d'infra n'a bougé"
- Laisser le rapport ouvert sans le sauvegarder dans `docs/friday-audits/`
- Utiliser `/production-audit` sans avoir d'abord lu la liste des fichiers infra touchés

## Voir aussi

- Skill : `security-scan` — scan config Claude
- Skill : `security-review` — review code sur endpoints
- Skill : `repo-scan` — santé architecturale du code source
- Skill : `production-audit` — readiness infra/déploiement
- Skill : `refactor-clean` — dette et code mort
- Agent : `comment-analyzer` — dérive des commentaires (Phase 4)
- Skill : `update-codemaps` — codemaps à jour
- Skill : `update-docs` — documentation à jour
- Skill : `skill-comply` — respect empirique des règles (Phase 7, mensuel)
- Skill : `skill-stocktake` — pertinence des skills/commandes (Phase 7, mensuel)
- Skill : `rules-distill` — patterns récurrents → règles (Phase 7, mensuel, après skill-stocktake)
- Skill : `eval-harness` — éval formelle si besoin identifié (Phase 7, mensuel)
- Rapport de référence : `docs/friday-audits/` (historique)
