# TODO — points en attente

Ouvert le 2026-08-26, suite au chantier de réorganisation architecture
(`CHANTIER_ARCHITECTURE.md`), à l'intégration du merge `raf5` (segmentation U-Net), puis à
la récupération de la suite du travail de Rafael sur `origin/raf5` (segmentation-service,
fixes GPU/MLflow/DagsHub). Chaque point ci-dessous a été identifié en session mais
volontairement laissé de côté (décision à prendre, hors périmètre du moment, ou correction
non triviale).

## Décisions en attente

### 1. `params.yaml` — `max_samples_per_class: 500` restreint le dataset d'entraînement

Récupéré depuis `origin/raf5` (utilisé pour stabiliser le pipeline pendant le debug GPU).
Cap le dataset brut à 500 images/classe avant augmentation — utile pour itérer vite, mais
**à repasser à `null` (dataset complet) avant tout entraînement final destiné à la
soutenance**, sous peine de modèle sous-entraîné par rapport aux résultats déjà présentés
(cf. `frontend/page/04_Machine_learning_et_optimisation`).

### 2. `trainer/requirements.txt` — hash-lock abandonné

`pip-compile --generate-hashes` sur `trainer/requirements.in` (mlflow 3.15.1 + dvc[s3] +
jupyterlab + albumentations + seaborn + wheels CUDA nvidia-cudnn/cublas/cufft) a été
interrompu après 15+ Go téléchargés et 12+ minutes sans converger — coût disproportionné
vu que `trainer/Dockerfile` n'utilise pas `--require-hashes` (le lock n'était donc qu'un
"bonus" reproductibilité, pas un besoin fonctionnel). `trainer/requirements.txt` est
maintenant une liste de versions à plat (validée par Rafael sur son vrai GPU RTX 3060),
pas un lockfile pip-compile. Si le hash-lock redevient souhaité : relancer
`pip-compile --generate-hashes` en conteneur Linux avec beaucoup de temps/bande passante
disponibles, ou épingler manuellement chaque wheel nvidia à une version précise pour
réduire l'espace de résolution.

### 3. Bump TensorFlow 2.18→2.21 / MLflow 2.19.0→3.15.1 — jamais testé par un vrai build

Récupéré depuis `origin/raf5` (nécessaire pour le driver CUDA 13.1 de la machine de
Rafael) et appliqué à `infrastructure/docker/base/Dockerfile` +
`infrastructure/docker/mlflow/Dockerfile` + `trainer/requirements.in`. Validé par Rafael
sur sa machine, **mais jamais rebuild ni testé sur cette machine** (aucun GPU disponible
ici pour vérifier). Un `docker compose build trainer mlflow base` avant la prochaine
session d'entraînement réelle est nécessaire pour confirmer que rien ne casse côté image.

## Vérifications non faites

### 4. `dvc dag` / `dvc repro` jamais lancés

La cohérence du graphe `dvc.yaml` n'a été vérifiée que statiquement (lecture,
`yaml.safe_load`). `dvc.lock` est resté intouché — il référence encore l'ancienne
structure (`backend/src/ds_covid`, `scripts/`) et sera automatiquement régénéré (chemins +
hashes) au prochain `dvc repro` réel. Un `dvc dag` (léger, ne nécessite pas les données)
confirmerait que DVC résout bien tous les chemins actuels avant de lancer un `dvc repro`
complet (lourd : pipeline sur 42 330 images, GPU requis pour les stages `train`/
`train_segmentation`).

### 5. CI segmentation-service jamais déclenchée réellement

`lint_seg`/`test_seg` + entrée `segmentation-service` dans la matrice `build` de
`cicd.yml` ajoutés par cohérence (raf5 ne l'avait pas câblé), mais jamais vus tourner en
vrai sur GitHub Actions — à surveiller au prochain push/PR.

## Bugs signalés, non corrigés (hors périmètre du moment)

### 6. `ops/check_quality.sh` — scanne `frontend/.venv`, crash sur fichier mal encodé

`make lint-full` (dépend de `setup-fe`) crée `frontend/.venv`, que le check de structure/
code-smell de `check_quality.sh` scanne sans l'exclure (aucun filtre `.venv` dans son
parcours de `frontend/`). Deux symptômes : faux positifs "arborescence trop profonde" sur
les paquets installés, et un `UnicodeDecodeError` qui fait planter `make lint-full` sur un
fichier `.py` mal encodé quelque part dans `frontend/.venv/lib/.../site-packages/`.
Reproductible sur toute machine où `frontend/.venv` existe localement.

### 7. 4 findings `ruff` mineurs (code du merge `raf5`, auto-fixables)

```
backend/app/config.py:3:1: I001 [*] Import block is un-sorted or un-formatted
backend/app/config.py:47:23: UP045 [*] Use `X | None` for type annotations
backend/app/features/preprocessing.py:74:25: UP045 [*] Use `X | None` for type annotations
backend/app/features/preprocessing.py:80:23: UP045 [*] Use `X | None` for type annotations
```

Note : `backend/app/features/preprocessing.py` a depuis été remplacé par la version
autonome (appel HTTP segmentation-service) — revérifier si ces lignes précises existent
encore avant d'appliquer `ruff check --fix`.

### 8. Nombreuses lignes >88 caractères dans le code du merge `raf5`

`predict.py`, `config.py`, `features/preprocessing.py`, `models/loader.py` — dépassent la
limite `pylint` (`max-line-length = 88`). `ruff` les ignore (E501 exclu du projet), mais
`pylint`/`make lint-full` les signalerait. Préexistant, pas introduit par ce chantier.

## Audit qualité du refactor de Rafael (segmentation U-Net) — findings restants

Fait par l'agent `mle-reviewer` le 2026-08-26 sur l'état d'alors (segmentation en process
dans le backend). Le point bloquant a été corrigé immédiatement. Les points 9-12
concernent `trainer/scripts/train_segmentation.py` et `trainer/src/ds_covid/segmentation.py`
— inchangés par la récupération de la suite de `raf5`, donc toujours valides.

### 9. [IMPORTANT] `ModelCheckpoint` recréé à chaque phase — perte de comparaison inter-phases

`trainer/scripts/train_segmentation.py` (phase 1 puis phase 2) : chaque `model.fit()`
reçoit une **nouvelle** instance de `ModelCheckpoint(..., save_best_only=True)` — Keras
réinitialise son "best" interne à +inf à chaque instanciation, donc la phase 2 ne sait rien
du meilleur point de la phase 1. Si le fine-tuning démarre moins bien que la phase 1
(risque documenté dans le docstring du fichier : "le val_dice s'effondre en 1-2 epochs si
on dégèle tout dès le début"), la 1ère epoch de phase 2 écrase quand même `model_path` sans
comparaison avec le vrai meilleur des deux phases.
Fix : réutiliser la même instance de callback entre les deux `fit()` (Keras conserve
`.best`), ou l'initialiser manuellement avec la meilleure val_loss de phase 1.

### 10. [IMPORTANT] Métriques loguées MLflow potentiellement différentes du modèle sauvegardé

`trainer/scripts/train_segmentation.py` logue `val_dice`/`val_iou`/`val_loss` de la
**dernière** epoch de la phase 2, mais `EarlyStopping(restore_best_weights=True)` restaure
en mémoire les poids de la **meilleure** epoch, et `model.load_weights(model_path)` (juste
avant le log MLflow) recharge encore un troisième état possible (sujet au bug du point 9).
Fix : recalculer dice/iou APRÈS `model.load_weights(model_path)`, juste avant de logger
(`evaluate_segmentation.py` le fait déjà correctement sur le test set).

### 11. [IMPORTANT] Aucun test sur les fonctions ML cœur de la segmentation

Zéro test unitaire sur `dice_coef`, `dice_loss`, `combined_loss`, `iou_metric`,
`clean_mask`, `collect_pairs`, `load_pair` (`trainer/src/ds_covid/segmentation.py`) ni sur
`MemmapSequence` (`trainer/src/ds_covid/data.py`) — aucun `trainer/tests/` n'existe.
Fix : `trainer/tests/test_segmentation.py` avec masks synthétiques (dice=1 sur masks
identiques, dice=0 sur masks disjoints, `clean_mask` qui élimine bien un îlot parasite).
Note : `segmentation-service/tests/` (récupéré depuis raf5) couvre `clean_mask` et le
`ModelLoader` côté service HTTP — mais pas le pipeline d'entraînement lui-même.

### 12. [MOYEN] Aucune passerelle de promotion sur l'évaluation du U-Net

`trainer/scripts/train_segmentation.py` enregistre le modèle dans le MLflow Model Registry
quelle que soit la qualité mesurée — pas de seuil minimum dice/iou, pas de comparaison au
modèle en prod. Même manque que sur le pipeline de classification.

### 13. [MOYEN] Triple duplication `params.yaml` / `backend/app/config.py` / `segmentation-service/config.py`

Depuis la récupération de la suite de raf5, la config `img_size`/`clean_mask_*` existe
maintenant à **trois** endroits distincts (`params.yaml` section `preprocess`/
`segmentation`, `backend/app/config.py`, `segmentation-service/src/segmentation_service/
config.py`) — cohérents aujourd'hui par inspection, rien ne garantit qu'ils le restent au
prochain réentraînement. Un futur changement de `img_size` dans `params.yaml` doit être
répercuté manuellement aux deux services, sans filet.
Fix : test qui charge `params.yaml` et vérifie l'égalité avec les defaults de chaque
`Settings`, ou source unique lue directement depuis `params.yaml` par les deux services.

## Fait — pour mémoire (ne pas rouvrir sans raison)

- `ops/data/{models,processed}/.gitkeep` accidentels → supprimés (`20ef63e`)
- Incohérence volume streamlit `/app/frontend` vs `WORKDIR /workspace` → corrigée (`2b1e65d`)
- Merge `raf5` (instantané ancien) intégré, conflit `backend/Dockerfile` résolu → `1bd8474`
- Bug démarrage backend (`lifespan` dupliqué sans import `asynccontextmanager`) → corrigé
  dans `1bd8474`, puis re-corrigé proprement par la version raf5 de `lifespan.py`
- **[BLOQUANT]** `MemmapSequence` dupliquée dans `trainer/scripts/train.py` écrasait
  l'import `ds_covid.data.MemmapSequence` (fix déjà validé par Steven sur `raf5`, commit
  `dbe7415`, jamais rapatrié dans le merge) → réappliqué (`2c16d01`)
- Règle CLAUDE.md #9 précisée (copie sandbox ciblée, jamais par exclusion) → `650d596`
- **Suite complète de `origin/raf5` récupérée** (12 commits en avance sur le merge initial) :
  - `segmentation-service/` importé tel quel — nouveau microservice HTTP autonome
    (`POST /v1/segment`), remplace le chargement TensorFlow en process dans le backend
  - `backend/app/features/preprocessing.py` devient totalement autonome (plus d'import
    `ds_covid`/sys.path — mon fallback du matin, `08bb097`, devient obsolète et est
    remplacé) — **résout le point tensorflow-manquant de `backend/requirements-dev.txt`
    par suppression du besoin, pas par ajout de poids**
  - `backend/app/{lifespan,main,models/loader,config,api/health,api/predict}.py` +
    tests alignés sur l'appel HTTP (`SEGMENTATION_SERVICE_URL`)
  - `docker-compose.yml` : service `segmentation-service` ajouté, backend en dépend
  - `Makefile` : `setup-segmentation`/`test-segmentation`, `dvc-setup-dagshub`/
    `dvc-push-dagshub`/`dvc-pull-dagshub`, `dvc-repro`
  - `.dvc/config` : remote DagsHub ajouté
  - `trainer/gpu-entrypoint.sh` (nouveau) : contournement bug Docker Desktop/WSL2 driver
    NVIDIA — voir `docs/incidents/2026-08-25_gpu-training-cuda13.md`
  - Vrai fix "class_weight" : `ds_covid.data.MemmapSequence` calcule le `sample_weight`
    par batch (Keras 3 casse sur `class_weight=` direct avec un Sequence custom) —
    `trainer/scripts/train.py` mis à jour + `TqdmCallback`
  - Code mort supprimé : `ds_covid/{cli,visualization}.py`, `models.py` retrimé à
    `build_cnn` seul (vérifié sans autre consommateur avant suppression)
  - CI (`cicd.yml`) étendue pour `segmentation-service` (raf5 ne l'avait pas fait)
  - Commits : `baad934`, `3677140`, `f00e5a0`, `b248caa`
