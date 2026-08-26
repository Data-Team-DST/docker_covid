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

## Vérifications non faites

### 5. CI segmentation-service jamais déclenchée réellement

`lint_seg`/`test_seg` + entrée `segmentation-service` dans la matrice `build` de
`cicd.yml` ajoutés par cohérence (raf5 ne l'avait pas câblé), mais jamais vus tourner en
vrai sur GitHub Actions — à surveiller au prochain push/PR.

## Chantier post-soutenance — rôles et frontières des services

Ouvert le 2026-08-26 (`CHANTIER_INFRA_SERVICES.md`), **à traiter après la soutenance du
04/09/2026** (CLAUDE.md § Calendrier — pas de refactoring structurel risqué à l'approche de
la démo). Détail complet, constats vérifiés et options dans le fichier lui-même ; ici,
uniquement le suivi backlog.

### 14. `infrastructure/docker/base/` — `frontend` a-t-il vraiment besoin de l'image TF-GPU ?

Non vérifié : lister les imports réels de `frontend/**/*.py` et confronter à
`base/requirements.in`. Si confirmé que `frontend` n'a besoin que d'opencv/numpy/pandas/
pillow, lui donner un Dockerfile léger (`python:3.11-slim`, comme `backend`) et laisser
`base` (TensorFlow-GPU) à `trainer` seul.

### 15. `frontend` (streamlit) vs `dashboard` (Flask) — deux responsabilités mélangées dans `dashboard`

`dashboard` porte déjà backlog agile interne + façade produit (data explorer, prédicteur
live) avant même d'absorber le contenu streamlit. 3 options posées (scinder `dashboard`
d'abord / créer un service `demonstration/` dédié / migrer le contenu tel quel dans
`dashboard`). Prérequis avant de trancher : inventaire page par page de `frontend/page/`
(conserver pour soutenance vs jetable).

### 16. `data-service` — mélange lecture (stats/recherche) et opérations DVC (pull/push/repro)

Même famille de problème que le point 15, moins visible. Piste : scinder en `data-service`
(lecture seule) + `pipeline-service`/`dvc-service` (opérations DVC) — pas évident que ce
soit rentable pour la taille du projet, priorité la plus faible des 4.

### 17. `mlflow` — câblé en écriture seule, aucun flux retour vers le déploiement

`trainer` logue systématiquement dans MLflow (Postgres + MinIO + service dédié port 5000),
mais `backend` charge son modèle depuis un fichier `.keras` local, jamais depuis le Model
Registry. Cohérent avec la maturité MLOps actuelle (Phase 4 — Monitoring/Drift — pas encore
atteinte), pas une erreur. Question à trancher : rester en observation pure, ou câbler un
vrai flux registry → déploiement (backend/data-service interroge le stage `Production` au
lieu d'un chemin codé en dur) ? À clarifier en premier (conditionne si le point 14 vaut le
coût).

## Fait — pour mémoire (ne pas rouvrir sans raison)

- **2026-08-26, #3 — bump TF 2.18→2.21 / MLflow 2.19.0→3.15.1, rebuild + GPU confirmés**
  (non committé — build local uniquement, rien à committer). Correction d'une erreur de
  cette même session : cette machine a bien un GPU (RTX 3060, driver 591.86, CUDA 13.1,
  runtime Docker `nvidia` fonctionnel) — la note "aucun GPU disponible ici" écrite plus
  haut dans ce fichier était fausse. Rebuild fait **depuis cette branche** (pas `main`,
  qui n'a pas encore les commits du bump) :
  - `docker build -f infrastructure/docker/base/Dockerfile -t covid-xray-base:bump-verify .`
    → OK (`tensorflow/tensorflow:2.21.0-gpu`)
  - `docker compose -f infrastructure/docker-compose.yml --project-directory . build mlflow`
    → OK (`mlflow==3.15.1` confirmé via `pip show` dans l'image)
  - `docker build -f trainer/Dockerfile --build-arg BASE_IMAGE=covid-xray-base:bump-verify
    -t covid-xray-trainer:bump-verify trainer` → OK, installe bien `trainer/requirements.txt`
    actuel (liste à plat post-abandon hash-lock, cf. #2) sur le nouveau `base`
  - `docker run --gpus all covid-xray-trainer:bump-verify python -c "..."` →
    `TF 2.21.0` / `MLflow 3.15.1` / `GPUs detected: [PhysicalDevice(... GPU:0 ...)]`
  - Images taguées `:bump-verify` laissées en local (pas nettoyées, faible coût) ; un
    conteneur mlflow différent tournait déjà (sain, 4h+ d'uptime) — non touché.
- **2026-08-26, traitement des points #4/6/7/8/9/10/11/12/13 (non committé)** — tout
  vérifié en sandbox jetable (conteneur Docker, mounts en lecture seule, CLAUDE.md #9),
  jamais en écrivant dans un venv réel :
  - **#4** `dvc dag` exécuté (image `trainer` en conteneur, repo monté en lecture seule) —
    les 6 stages du graphe se résolvent sans erreur.
  - **#6** `ops/check_quality.sh` : exclusion `.venv`/`venv`/`__pycache__` des 3 boucles
    `find` de `check_structure_complexity` (pattern `-prune`) + du scan Python de
    `check_code_smell` ; `except OSError` élargi à `except (OSError, UnicodeDecodeError)`
    dans `check_quality.sh` et `ops/check_code_smell_parser.py::get_file_annotation`.
    Vérifié isolément (arbre de test avec `.venv` simulé → bien exclu).
  - **#7** `ruff check --fix backend/app/config.py backend/app/features/preprocessing.py`
    appliqué (I001 + 8× UP045, plus nombreux que les 4 lignes listées à l'origine —
    `preprocessing.py` avait grossi depuis). `ruff check backend/app/` → clean. Suite
    backend complète rejouée en conteneur (`python:3.11-slim`, deps hash-lockées) : 71
    tests passés, coverage 94.41% (seuil 80%).
  - **#8** Revu : gate `pylint` informative uniquement en CI (`|| true` assumé dans
    `cicd.yml`), ne bloque rien. Laissé tel quel, pas d'action nécessaire.
  - **#9** `trainer/scripts/train_segmentation.py` : une seule instance de
    `ModelCheckpoint` (`checkpoint_cb`) réutilisée entre phase 1 et phase 2. Vérifié par
    smoke-test dédié (U-Net réel, données synthétiques, sandbox conteneur) :
    `checkpoint_cb.best` passe de 1.1852 (fin phase 1) à 1.1830 (fin phase 2) — cumulatif,
    ne régresse pas.
  - **#10** Métriques `val_dice`/`val_iou`/`val_loss` recalculées via
    `model.evaluate(val_seq_ft, verbose=0, return_dict=True)` juste après
    `model.load_weights(model_path)`, au lieu de lire `history_finetune` (dernière epoch,
    potentiellement différente du modèle réellement sauvegardé). Clés `return_dict`
    (`loss`/`dice_coef`/`iou_metric`) confirmées empiriquement dans le même smoke-test ;
    `eval_metrics["loss"]` retombe exactement sur `checkpoint_cb.best`.
  - **#12** Ajout `segmentation.min_val_dice: 0.5` dans `params.yaml` (**valeur
    provisoire, à recalibrer par Steven** une fois de vraies métriques disponibles — pas
    de baseline réelle sur cette machine, pas de GPU) + passerelle dans
    `train_segmentation.py` : sous le seuil, `mlflow.keras.log_model(...)` est appelé
    **sans** `registered_model_name` (reste artefact du run, n'entre pas dans le Model
    Registry) et un `[WARN]` est loggé. Comparaison à un modèle "Production" existant
    volontairement hors scope (cf. chantier #17 ci-dessous — mlflow reste write-only pour
    l'instant, sujet distinct).
  - **#11** `trainer/tests/test_segmentation.py` (14 tests : dice_coef/dice_loss/
    combined_loss/iou_metric sur masks synthétiques identiques/disjoints, clean_mask,
    collect_pairs, load_pair) + `trainer/tests/test_data.py` (7 tests : MemmapSequence —
    `__len__`, batching, sous-ensemble d'indices, shuffle, class_weight) +
    `trainer/tests/conftest.py` (sys.path vers `trainer/src`, `trainer/` n'étant pas
    câblé dans `[tool.pytest.ini_options]` du `pyproject.toml` racine). 21/21 verts en
    sandbox (image `ghcr.io/data-team-dst/covid-xray-trainer:latest`, pytest installé à
    la volée, repo monté en lecture seule).
  - **#13** Pas de source unique (rejeté : forcerait soit un import Python cross-service
    interdit par R8, soit une refonte du chargement de config plus large que le périmètre
    du jour) — tests de cohérence à la place :
    `backend/tests/unit/test_config.py::test_defaults_match_params_yaml_preprocess_section`
    et `segmentation-service/tests/test_config.py::test_defaults_match_params_yaml`,
    chacun ne lisant que `params.yaml` + la config de son propre service. Vérifiés en
    sandbox : backend 71 tests / 94.41% cov, segmentation-service 16 tests / 92.94% cov.
  - **Non couvert par cette session** (pas de GPU, pas de vraies données ici) : un run
    réel `dvc repro` (`train_segmentation`) sur le dataset complet reste la seule
    validation de bout en bout des points #9/#10/#12 en conditions réelles — les smoke-
    tests ci-dessus valident la logique, pas la performance du modèle.
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
