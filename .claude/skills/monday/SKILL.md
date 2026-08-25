---
name: monday
description: Rituel lundi matin — reprend le dernier audit friday, croise avec le backlog sprint, adapte la profondeur du check selon l'activité du weekend, génère un plan de semaine actionnable dans docs/monday-plans/.
origin: project
---

# /monday — Rituel lundi matin

Complément naturel de `/friday`. Là où friday **mesure et priorise**, monday **planifie et démarre**.
Il ne réinvente pas la roue : il exploite le travail de vendredi et le met en action.

## Déclencheur

`/monday` — à lancer chaque lundi matin, avant de commencer à coder.

## Philosophie

- **Friday a fait le constat** → monday fait le plan
- **Adaptatif** : la profondeur du check technique dépend de l'activité depuis vendredi
- **Actionnable** : le rapport se termine par une tâche de démarrage explicite
- **Sprint-aware** : croise les actions vendredi avec `dashboard/backlog.yaml`
- Durée cible : 15-30 min selon le volume de commits weekend

---

## Séquence d'exécution

### Étape 1 — Chargement du rapport friday (~2 min)

```bash
# Trouver le rapport friday le plus récent
ls -t docs/friday-audits/*.md | head -1
```

Lire le fichier trouvé. Extraire :
- Le tableau **"Actions prioritisées"** (P1, P2, P3)
- Le **Bilan** (dernière ligne du rapport)
- Les métriques semaine (lint, coverage)

Si aucun rapport friday n'existe → passer directement à l'Étape 3 en mode
"premier lundi sans rapport" et signaler dans le plan généré.

---

### Étape 2 — Activité depuis vendredi (check adaptatif, ~3-10 min)

```bash
# Compter les commits depuis vendredi
git log --oneline --since="last friday" | wc -l

# Détail des commits et fichiers touchés
git log --oneline --since="last friday" --name-only
```

**Décision selon le nombre de commits N :**

| N commits | Action | Raison |
|---|---|---|
| **0** | Aucun re-check | Rapport friday = vérité absolue |
| **1-3** | `git diff --name-only HEAD~N` → identifier les services touchés → `pylint` ciblé sur ces services uniquement (~2 min) | Vérification légère, ne pas dupliquer friday |
| **4+** | Lint + quick coverage sur les services touchés uniquement (pas `make quality` global) | Commits significatifs = état potentiellement différent de vendredi |

**Quick lint ciblé (si N ≥ 1)** — remplacer `SERVICE` par les services concernés :

```bash
# Exemple pour data-service et backend
cd data-service && .venv/bin/python -m pylint src/ --score=yes 2>/dev/null | tail -3
cd ../backend && .venv/bin/python -m pylint app/ --score=yes 2>/dev/null | tail -3
```

**Ne jamais lancer `make quality` complet dans cette étape.** C'est le domaine de `/friday`.

---

### Étape 3 — Contexte sprint (~3 min)

```bash
cat dashboard/backlog.yaml
```

Lire `dashboard/backlog.yaml`. Identifier :
- Le sprint actuel (section en cours)
- Les user stories non terminées
- Les items tagués `priorité: haute` ou `bloquant`

Croiser avec les actions friday : est-ce que les P1/P2 ont une US correspondante
dans le backlog ? Si oui, les lier dans le plan. Si non, signaler comme dette hors-sprint.

---

### Étape 3b — Sécurité agentic (si nouveau hook / MCP depuis vendredi, ~2 min)

Si les commits depuis vendredi touchent `.claude/hooks/`, `.mcp.json`, ou `.claude/settings*.json` :

```bash
# Vérifier tout nouveau hook ou MCP ajouté depuis vendredi
git diff --since="last friday" --name-only | grep -E "\.claude/hooks|\.mcp\.json|settings"

# Scan rapide sur les fichiers modifiés
grep -rn "ANTHROPIC_BASE_URL\|enableAllProjectMcpServers\|curl\|wget" .claude/hooks/ 2>/dev/null
```

Si des findings de sécurité agentic venaient d'un rapport friday → vérifier s'ils ont été traités.
Sinon, passer cette étape.

---

### Étape 4 — État courant du repo (~1 min)

```bash
git status --short
git stash list
```

Signaler tout fichier modifié non commité ou stash oublié — ces éléments doivent
apparaître dans la section "Blockers" du plan si présents.

---

### Étape 5 — Génération du plan (créer le fichier, ~5-10 min)

Créer le fichier `docs/monday-plans/YYYY-MM-DD.md` avec la date du lundi courant.

Structure obligatoire du plan :

```markdown
# Plan semaine YYYY-MM-DD

## Rappel findings vendredi

| # | Action | Service | P | Estimation | Statut |
|---|--------|---------|---|-----------|--------|
| 1 | ... | ... | P1 | 5 min | ⬜ À faire |
| 2 | ... | ... | P2 | 2h | ⬜ À faire |

<!-- Recopier le tableau "Actions prioritisées" du rapport friday.
     Changer le statut en "✅ Fait" pour les actions déjà traitées depuis vendredi. -->

## Ce qui a bougé depuis vendredi

<!-- Résumé git log --since="last friday" : N commits, services touchés -->
<!-- "Rien" si 0 commits -->

## Résultats lint post-weekend

<!-- Scores si un re-check a été lancé (Étape 2), sinon "Inchangé — voir rapport friday" -->

## Contexte sprint

<!-- Sprint en cours, US actives, items bloquants issus de backlog.yaml -->

## Plan de la semaine

### Priorité 1 — À faire aujourd'hui
<!-- Actions P1 du rapport friday + bloquants sprint -->

### Priorité 2 — À faire cette semaine
<!-- Actions P2 + US sprint en cours -->

### Priorité 3 — Backlog / si le temps le permet
<!-- Actions P3 + dette long terme -->

## Blockers à anticiper

<!-- Fichiers non commités, stash oubliés, dépendances inter-services, CI en attente -->
<!-- "RAS" si rien -->

## Tâche de démarrage recommandée

**→ [Nom exact de la tâche, service concerné, temps estimé]**

<!-- La première chose à faire maintenant. Une seule, actionnable immédiatement.
     Préférer P1 ou P2 court (< 2h) pour démarrer sur une victoire rapide. -->
```

---

## Ce que ce skill ne fait PAS

- Il ne lance pas `make quality` complet (domaine de `/friday`)
- Il ne modifie pas le code — il planifie seulement
- Il ne commit pas le rapport (vous décidez)
- Il ne ferme pas les issues du backlog — il indique quoi faire

## Anti-patterns à éviter

- Lancer `/monday` sans avoir lu le rapport friday d'abord (l'Étape 1 est obligatoire)
- Re-lancer tous les tests même si 0 commits depuis vendredi (inutile et lent)
- Générer un plan vague sans tâche de démarrage claire
- Mettre plus de 3 items en "Priorité 1" — si tout est P1, rien n'est P1

## Voir aussi

- Skill : `friday` — audit hebdomadaire de référence
- Skill : `repo-scan` — santé architecturale (si `/monday` détecte un besoin)
- Rapport source : `docs/friday-audits/` (dernier fichier)
- Plan généré : `docs/monday-plans/YYYY-MM-DD.md`
