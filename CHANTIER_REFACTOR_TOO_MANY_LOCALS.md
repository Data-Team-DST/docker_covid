# Chantier — Réduire les fonctions `too-many-locals` du frontend

> Document de cadrage, pas un plan d'exécution. Destiné à être repris par une autre conversation
> Claude Code. Rien n'a été commencé côté code — volontairement laissé de côté le 2026-08-24 à
> 11 jours de la soutenance (2026-09-04), pour ne pas risquer une régression sur du code
> Streamlit fonctionnel et non couvert par des tests automatisés.

## Contexte

Audit pylint du 2026-08-24 (dépendances `frontend/requirements.txt` installées, config réelle
du repo via `pyproject.toml`) : 6 fonctions dépassent le seuil `too-many-locals` (R0914,
seuil pylint par défaut = 15 variables locales). Toutes sont dans des fonctions de rendu
Streamlit (beaucoup de variables = beaucoup de widgets UI déclarés localement, pattern courant
mais qui grossit vite).

| Fichier | Fonction | Locales / seuil |
|---|---|---|
| `frontend/page/02_donnees/_data_utils.py` | `run_full_dataset_scan` (ligne ~107) | 17/15 |
| `frontend/page/02_donnees/_ui.py` | `render_quick_sample` (ligne ~32) | 26/15 |
| `frontend/page/04_Machine_learning_et_optimisation/_confusion_matrices.py` | (ligne ~70) | 17/15 |
| `frontend/page/06_cicd/_pipeline_create.py` | `_render_config_ui` (ligne ~21) | 20/15 |
| `frontend/page/06_cicd/_pipeline_load.py` | `render_load_mode` (ligne ~8) | 23/15 |
| `frontend/page/06_cicd/_pipeline_steps.py` | (ligne ~5) | 17/15 |

**Note** : `06_cicd/_pipeline_create.py` et `_pipeline_load.py` font partie de la fonctionnalité
"pipeline builder" actuellement cassée (import mort vers des classes supprimées — voir
l'historique de conversation du 2026-08-24, ou un éventuel `CHANTIER_*` dédié à ce bug si créé
séparément). **Vérifier si ce bug a été corrigé avant de refactorer ces deux fichiers** — pas la
peine de nettoyer du code dont on ne sait pas encore s'il doit être réparé ou supprimé.

Chaque fonction porte actuellement `# pylint: disable=too-many-locals` sans autre
justification que le seuil dépassé — recensé comme dette dans
`.claude/rules/python/sonarqube.md`.

## Pourquoi ce n'est pas un simple nettoyage automatique

Contrairement aux disables déjà retirés le 2026-08-24 (`broad-exception-caught`,
`missing-function-docstring`, `line-too-long`), réduire le nombre de variables locales demande
un vrai refactor : extraire des sous-fonctions, regrouper des variables apparentées dans un
dict/dataclass, ou déplacer de la logique de calcul hors de la fonction de rendu. Ce n'est pas
mécanique — un mauvais découpage peut introduire un bug silencieux dans du code Streamlit sans
filet de tests automatisés (`frontend/` n'a pas de suite pytest à ce jour, cf. job `test_fe`
dans `cicd.yml`, `continue-on-error: true`, "FE tests pas encore implementes").

## Approche recommandée pour qui reprend ce chantier

1. **Vérifier le statut du bug `06_cicd` pipeline builder** avant de toucher
   `_pipeline_create.py`/`_pipeline_load.py` (voir note ci-dessus).
2. Pour chaque fonction, avant de refactorer : lancer l'app Streamlit
   (`streamlit run frontend/streamlit_app.py`) et noter le comportement actuel de la page
   concernée (captures d'écran si possible) — c'est le seul "test de non-régression"
   disponible pour ce code.
3. Refactorer une fonction à la fois, dans son propre commit, en relançant l'app après chaque
   changement pour confirmer visuellement qu'il n'y a pas de régression.
4. Pattern d'extraction à privilégier : sortir les blocs `with st.columns(...)`/
   `with st.container(...)` indépendants en sous-fonctions `_render_xxx(...)`, plutôt que de
   regrouper artificiellement des variables dans un dict juste pour faire baisser le compteur
   (ça masquerait le problème sans clarifier le code — cf. `.claude/rules/common/coding-style.md`
   § KISS).
5. Une fois `too-many-locals` réellement résolu (pas juste re-disable avec un seuil relevé),
   retirer le `# pylint: disable=too-many-locals` correspondant et mettre à jour
   `.claude/rules/python/sonarqube.md` (section sur l'exemption `frontend/page/*.py`) pour
   retirer la mention de ces occurrences.

## Ce que ce document ne fait pas

- Il ne propose pas de découpage précis fonction par fonction — à faire au moment de la reprise,
  en lisant le code courant (peut avoir changé depuis le 2026-08-24).
- Il ne touche à aucun fichier de code.
