# Chantier — Décider du sort du "pipeline builder" cassé (page 06_cicd)

> Document de cadrage, pas un plan d'exécution. Audit fait le 2026-08-24, rien touché côté code
> en attendant la décision de Steven. Destiné à être repris par une autre conversation.

## Le bug

`frontend/page/06_cicd/_pipeline_load.py` et `_pipeline_steps.py` font :
```python
from src.features.St_Pipeline.Transformateurs import (
    ImageAnalyser, ImageAugmenter, ImageFlattener, ImageHistogram, ImageMasker,
    ImageNormalizer, ImagePathLoader, ImagePCA, ImageResizer, RGB_to_L,
    SaveTransformer, TrainTestSplitter, TupleToDataFrame,
)
```
Cet import est cassé et fait planter la page "🆕 Créer un nouveau pipeline" /
"📂 Charger un pipeline existant" de la page **06_cicd ("CI/CD et qualité logicielle")** dès
qu'un utilisateur clique dessus.

## Pourquoi c'est cassé (audit du 2026-08-24)

Deux problèmes empilés, pas un seul :

1. **Les classes ont été supprimées ce matin** — commit `d82766b` (Rafael, "chore(backend):
   supprimer le code mort dans backend/src"), qui a retiré
   `backend/src/features/St_Pipeline/Transformateurs/` (13 classes : `ImageAnalyser`,
   `ImageAugmenter`, `ImagePCA`, `SaveTransformer`, `TrainTestSplitter`,
   `ImagePathLoader`/`TupleToDataFrame` dans `loaders.py`, `ImageFlattener`/`ImageMasker`/
   `ImageNormalizer`/`ImageResizer`/`RGB_to_L` dans `processing/`, `ImageHistogram` dans
   `visualization/`). Justification documentée dans le commit : "`backend/app/` (la vraie API)
   n'importe rien de `backend/src`". **Entièrement récupérable via
   `git show 3eb7438359de84db45036a5b0490671b5e43300c:backend/src/features/St_Pipeline/Transformateurs/<fichier>`**
   (commit juste avant la suppression).
2. **Même restaurées, l'import resterait cassé** — `_PROJECT_ROOT` (calculé dans
   `frontend/page/06_cicd/__init__.py:28`, `Path(__file__).parent.parent.parent.parent`)
   pointe vers la **racine du repo**, ajoutée à `sys.path`. Or `from src.features...` cherche
   un package `src/` **à la racine du repo** — qui n'existe plus depuis la migration Phase 1
   → microservices (seuls `backend/src/` et `data-service/src/` existent aujourd'hui). Ce
   second problème est antérieur à la suppression de ce matin : il date très probablement de
   cette migration elle-même.

**Ce que ça implique** : la suppression de ce matin n'est pas la cause racine, elle a juste
ajouté une seconde couche de casse à quelque chose déjà non-fonctionnel depuis un moment.

## Est-ce que ça vaut le coup d'être réparé ? (éléments pour trancher)

- **Aucune US dans `dashboard/backlog.yaml`** ne référence ce pipeline builder interactif —
  ni sous ce nom, ni sous un nom approchant. Aucune mention dans `README.md` ou `docs/`.
- **Ajouté par Steven lui-même**, commit `ac72ebc`, 2026-03-19 — très tôt dans le projet
  (époque où `src/` vivait encore à la racine), probablement une fonctionnalité exploratoire
  greffée sur la page pédagogique CI/CD, pas un livrable central.
- Le titre réel de la page (`frontend/page/06_cicd/__init__.py:34`,
  `colored_header(label="CI/CD et qualité logicielle", ...)`) suggère que le cœur de la page
  est une présentation pédagogique du pipeline CI/CD du projet — le pipeline builder sklearn
  interactif est une fonctionnalité annexe, pas le sujet principal.
- **Personne n'a signalé cette page cassée** avant cet audit — ni dans les rapports `/friday`
  précédents (aucun n'existait avant aujourd'hui), ni ailleurs.

## Options (à trancher avec Steven avant d'exécuter quoi que ce soit)

### Option A — Restaurer proprement
1. `git checkout 3eb7438359de84db45036a5b0490671b5e43300c -- backend/src/features/St_Pipeline/Transformateurs/`
2. Corriger `_PROJECT_ROOT` dans `06_cicd/__init__.py` pour pointer vers `backend/` au lieu de
   la racine du repo (ou déplacer le package ailleurs — à décider selon où le reste de
   `backend/src/` doit vivre à terme).
3. Tester réellement : charger un `.pkl` existant si un exemple est disponible, et créer un
   nouveau pipeline de bout en bout depuis l'UI.
4. Retirer le disable `unused-import` désormais injustifié dans `_pipeline_load.py` (voir
   `.claude/rules/python/sonarqube.md`).

Risque : ressusciter du code que Rafael a explicitement qualifié de mort ce matin, sur la base
d'un audit qui n'avait pas vu cette dépendance frontend — vérifier avec lui qu'il n'y a pas
d'autre raison de l'avoir supprimé.

### Option B — Désactiver proprement
Remplacer le crash par un message "fonctionnalité indisponible" dans les deux fichiers,
sans rien restaurer. Rapide, mais le pipeline builder reste inutilisable définitivement sauf
nouvelle intervention.

### Option C — Couper toute la fonctionnalité pipeline builder
Si l'audit ci-dessus est jugé suffisant pour conclure que c'est un reliquat sans utilisateur,
retirer purement `_pipeline_create.py`, `_pipeline_load.py`, `_pipeline_steps.py`,
`_pipeline_exec.py`, `_pipeline_ui.py` et le radio "Mode de travail" dans `_sections.py`/
`__init__.py`, pour ne garder que la présentation pédagogique CI/CD de la page. Nettoie aussi
le disable `too-many-locals` associé (voir `CHANTIER_REFACTOR_TOO_MANY_LOCALS.md`, deux des
six fonctions concernées disparaîtraient avec ce fichier).

## Ce que ce document ne fait pas

- Il ne tranche pas entre A/B/C — c'est une décision produit pour Steven.
- Il ne touche à aucun fichier de code.
