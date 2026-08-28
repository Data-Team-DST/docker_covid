# Chantier — Rôles et frontières des services (base, frontend/dashboard, DVC, mlflow)

Ouvert le 2026-08-26, **à traiter après la soutenance du 04/09/2026** (CLAUDE.md §
Calendrier : pas de refactoring structurel risqué à quelques jours de la démo). Constat et
options seulement — aucune modification appliquée. Origine : questions posées par Steven en
session sur la place de `base`, `frontend`/`dashboard`, DVC et `mlflow` dans l'architecture.

Les 4 points sont liés : tous posent la même question de fond — *est-ce que ce composant a
une responsabilité unique et claire, et si un service a besoin d'une capacité qui vit
ailleurs, passe-t-il bien par un appel réseau plutôt que par un partage de build/code ?*
C'est le principe déjà appliqué à l'extraction de `segmentation-service` (US du 2026-08-26) :
au lieu d'embarquer TensorFlow dans le backend, un service dédié expose `POST /v1/segment`
et le backend l'appelle en HTTP.

## 1. `infrastructure/docker/base/` — image partagée `trainer`/`frontend`, probablement le mauvais pattern

**Résolu le 2026-08-27.** Confirmé par grep exhaustif de `frontend/**/*.py` (hors `.venv`) :
imports réels = `PIL`, `numpy`, `pandas`, `plotly`, `streamlit`, `streamlit_extras`,
`kagglehub` + stdlib — zéro `tensorflow`/`cv2`/`keras`. `frontend/Dockerfile` passe de
`FROM ${BASE_IMAGE}` (`tensorflow/tensorflow:2.21.0-gpu`, 8,48 Go) à `python:3.11-slim`,
avec un `frontend/.dockerignore` ajouté au passage (absent partout dans le repo — bloquait
le build à cause de `frontend/.venv/` local). `scikit-learn`/`requests` retirés de
`requirements.in` (jamais importés ; `requests` reste en transitif via streamlit/kagglehub,
normal). `cicd.yml` simplifié (plus besoin du login PAT dédié au pull de `covid-xray-base`
pour frontend). Vérifié en conditions réelles : build OK, **image 9,13 Go → 969 Mo (-89%)**,
conteneur démarre, healthcheck + page principale répondent 200.

**Constat.** `base` = `tensorflow/tensorflow:2.21.0-gpu` + libs système (git, build-essential,
libgl1) + stack Python commune (`numpy`, `pandas`, `scikit-learn`, `matplotlib`,
`opencv-python`, `pillow` — voir `infrastructure/docker/base/requirements.in`). Ce n'est pas
un service (pas de port, pas d'ENTRYPOINT, jamais lancé seul) — c'est une couche de build
partagée que `trainer/Dockerfile` et `frontend/Dockerfile` consomment via `ARG BASE_IMAGE`.

**Le problème.** `frontend` (streamlit) ne fait aucune inférence live et n'appelle jamais le
backend ni aucun autre service (vérifié par grep lors de l'audit streamlit vs dashboard du
2026-08-26 : zéro usage de `requests`/`BACKEND_URL`/`DATA_SERVICE_URL`). Les pages qui
montrent des résultats de modèles (04, 05) affichent des images statiques pré-générées, pas
du calcul en direct. Seule la page `02_données` fait du traitement d'image réel (luminosité/
contraste/entropie, overlay de mask), qui ne nécessite a priori qu'opencv/numpy/pillow —
**pas TensorFlow-GPU**. Embarquer `frontend` sur une image TF-GPU complète (téléchargement
lourd, image lourde) pour ces besoins est probablement disproportionné.

**Non vérifié** (à faire avant de trancher) : lister précisément tous les imports de
`frontend/**/*.py` et confronter à `base/requirements.in` — confirmer qu'aucune page
n'importe réellement `tensorflow`/`cv2` au-delà de ce qu'un `pip install opencv-python-headless
numpy pandas pillow matplotlib` autonome couvrirait.

**Piste** : si confirmé, donner à `frontend` son propre Dockerfile léger (`python:3.11-slim`,
comme `backend`), sans `ARG BASE_IMAGE`. `trainer` garde sa stack GPU pour lui seul —
`base` devient soit inutile (fusionné dans `trainer/Dockerfile` directement), soit renommé
pour ce qu'il est vraiment ("l'image GPU de trainer"), plutôt que de prétendre être une
ressource partagée entre deux consommateurs qui n'en ont pas besoin au même degré.

## 2. `frontend` (streamlit) vs `dashboard` (Flask) — chantier de fond, pas un renommage

**Option C appliquée le 2026-08-28** (inventaire page par page fait, cf. session) — contenu
migré vers `dashboard` au fil de l'eau, pas de split de service ni de `demonstration/` dédié
(pas le temps avant la soutenance) :
- `01`/`04`/`05` (texte) : déjà condensés dans `/contexte` avant même cette session.
- **07 (conclusion critique/éthique)** : migré → nouvelle page `/conclusion`. Roadmap mise à
  jour pour ne plus présenter comme "futur" ce qui est déjà livré (versionnage données,
  pipeline MLOps).
- **Images 04/05** (5 matrices de confusion, architecture InceptionV3, courbes loss/accuracy,
  matrice deep learning, 2 visualisations LIME) : copiées dans `dashboard/static/img/`,
  intégrées dans `/contexte`.
- **02_données** (seule page avec calcul réel, pas juste des images statiques) : logique
  d'échantillonnage + métriques (luminosité/contraste/entropie/couverture masque) portée vers
  `data-service` (pas directement dans `dashboard`, pour respecter la frontière de service
  déjà établie) — nouveaux endpoints `/v1/data/sample` et `/v1/data/metrics`, section dédiée
  sur `/data` + galerie d'anomalies (8 images statiques).
- **03 (préprocessing)** : migré → nouvelle page `/preprocessing` (env Windows/WSL/Colab,
  masking avant/après, déséquilibre de classes, augmentation — 10 images statiques).
- **Non fait, volontairement** : 06 (CI/CD) — contenu périmé (présente Docker/CD/monitoring
  comme absents alors qu'ils existent). À réécrire ou abandonner, pas à migrer tel quel.
- `frontend/` (Streamlit) devient supprimable dès que 06 est tranché (réécrit ou abandonné) —
  c'est la seule page qui n'a plus d'équivalent dans `dashboard`.

**Constat déjà établi** (audit du 2026-08-26, avant récupération de `raf5`) : sur les 7 pages
streamlit, seules `01_accueil` et `02_données` ont un équivalent partiel dans `dashboard`. Les
5 autres (`03_preprocessing`, `04_Machine_learning_et_optimisation`, `05_Deep_learning_et_
Interprétabilité`, `06_cicd`, `07_conclusion`) — le contenu de présentation pour la soutenance
(modèles, matrices de confusion, LIME, conclusion/limites) — n'ont aucun équivalent dans
`dashboard`. Steven a choisi de garder `frontend/` pour l'instant (décision actée le
2026-08-26) précisément pour ne pas perdre ce contenu avant la démo.

**Le problème soulevé en session (2026-08-26)** : `dashboard` porte déjà **deux
responsabilités distinctes** avant même d'y ajouter le contenu streamlit :
- outil interne de gestion de projet (backlog agile, sprints, résolution de commits)
- façade orientée produit (data explorer, prédicteur live `/predict` → backend)

Un service qui fait les deux n'est pas un microservice au sens strict (single
responsibility). Ajouter le contenu de présentation streamlit par-dessus aggraverait ce
mélange plutôt que de le résoudre.

**Pistes à trancher ensemble (après soutenance)** :
- **Option A** : scinder `dashboard` d'abord (backlog interne / démo produit), migrer le
  contenu streamlit pertinent vers le côté "démo", puis supprimer `frontend/`.
- **Option B** : garder `dashboard` tel quel (outil interne, pas un "vrai" microservice au
  sens produit — accepté comme tel), et créer un nouveau service dédié `demonstration/`
  (ou équivalent) qui reprend le contenu de présentation de `frontend/` + le prédicteur live
  déjà présent dans `dashboard`, avant de retirer `frontend/`.
- **Option C** : ne rien changer côté découpage service, juste migrer le contenu texte/
  images de streamlit vers les templates `dashboard/` existants (le plus rapide, mais ne
  résout pas le mélange de responsabilités déjà identifié).

**Prérequis avant d'agir, quelle que soit l'option** : lister précisément, page par page de
`frontend/page/`, ce qui doit être conservé pour une soutenance (texte, images statiques,
graphiques régénérables) vs ce qui était de l'exploration jetable.

## 3. DVC — pourquoi pas son propre conteneur comme mlflow, et la même critique "single responsibility"

**Résolu le 2026-08-28.** Steven a tranché pour le split malgré la priorité la plus faible
signalée ci-dessous : nouveau service `dvc-service` (port 5003) créé sur le même patron que
`data-service`/`segmentation-service` (FastAPI, `main.py`/`api/v1/router.py`,
`logging_config.py` dupliqué, lockfile hash-locké régénéré en conteneur Linux jetable —
CLAUDE.md règle 9). `data-service` redevient strictement lecture seule (`/data/stats`,
`/data/image`, `/data/search`, `/data/sample`, `/data/metrics`) : `dvc[s3]` retiré de ses
dépendances (vérifié `grep dvc== requirements.txt` → 0 occurrence), `dvc_service.py` et
`entrypoint.sh` (config remote MinIO) supprimés, Dockerfile simplifié (plus de `git` ni
d'entrypoint). `dvc-service` porte `/v1/dvc/status`, `/v1/dvc/remotes`, `/v1/dvc/pull`,
`/v1/dvc/push`, `/v1/dvc/repro`.

**Frontière respectée (R8)** : les deux services ne partagent aucun filesystem/état — après
un `pull`/`repro` qui change les fichiers sur disque, `dvc-service` appelle `data-service` en
HTTP (`GET /v1/data/stats?refresh=true`, best-effort, `_invalidate_data_service_cache()`) pour
forcer un re-scan plutôt que de dépendre d'un montage partagé.

**Vérifié en conditions réelles** (jamais dans le repo réel, toujours en conteneur jetable ou
via `docker compose`, cf. CLAUDE.md règle 9) :
- `dvc-service` : build OK, démarre, `/health` répond, `/v1/dvc/status` exécute réellement
  `dvc status` en subprocess et retourne un résultat cohérent. Tests 14/14 verts, coverage
  92,57 % (≥80 %). `ruff check` propre.
- `data-service` : build OK (confirmé `dvc` absent des deps installées), démarre, `/health` et
  `/v1/data/stats` répondent (200, scan réel de 42 330 fichiers). Tests 26/26 verts, coverage
  83,27 % (≥80 %). `ruff check` propre.
- `docker compose up data-service dvc-service` (depuis la racine, `--project-directory .` —
  piège découvert : lancer depuis `infrastructure/` sans ce flag cherche `.env` au mauvais
  endroit) : les deux conteneurs démarrent sains, connectivité réseau interne confirmée
  (`dvc-service` → `http://data-service:5001` répond 200 via le nom de service Compose).
- `dashboard/app.py` : `DVC_SERVICE_URL` ajouté, `dvc_proxy()` cible bien `dvc-service:5003`.

**Bug réel trouvé et corrigé pendant la vérification** (pas un problème du split lui-même) :
`data_stats_service.py` importait encore `PROJECT_ROOT` depuis le `dvc_service.py` supprimé —
`ModuleNotFoundError` au démarrage de `data-service`. Corrigé en redéfinissant `PROJECT_ROOT`
localement dans `data_stats_service.py` (valeur identique, `Path(os.getenv("PROJECT_ROOT",
"/app"))`). Un deuxième bug était dans les **tests**, pas le code : `test_router.py` patchait
`router_module.CACHE_FILE`, qui n'a jamais existé sur `router.py` (seul `data_stats_service`
lit `CACHE_FILE` — `router.py` n'importe que `DATA_DIR`) — corrigé en ne patchant que
`data_stats_service.CACHE_FILE`, conforme au piège documenté dans
`.claude/rules/python/import_cascade.md` R13.

**Résolu le 2026-08-28 (suite immédiate).** Le cache JSON de `/v1/data/stats`
(`data_stats_service.py::save_cache`) ne persistait jamais en conditions `docker compose`
réelles — `/app/tmp` était créé par Docker en `root:root` (755) au moment du bind-mount de
`./tmp/logs:/app/tmp/logs` (le sous-dossier `logs` est en 777, mais pas son parent), et
`appuser` n'avait pas le droit d'y écrire `data_cache.json`. `save_cache()` avalait l'`OSError`
silencieusement (`except OSError: pass`) donc l'échec était invisible — chaque appel à
`/v1/data/stats` re-scannait intégralement les 42 330 fichiers (~140-170s) au lieu de servir
le cache. **Bug préexistant, confirmé identique avant le split** (même montage `./tmp/logs`
dans `git show HEAD:infrastructure/docker-compose.yml`, même chemin
`PROJECT_ROOT/tmp/data_cache.json`) — découvert seulement lors de la première vérification
bout-en-bout réelle de ce endpoint en conteneur.

**Fix appliqué** : une ligne dans `data-service/Dockerfile`
(`RUN mkdir -p /app/tmp && chown -R appuser:appuser /app`, juste avant le `COPY src/`) —
`/app/tmp` existe et appartient à `appuser` dès le build de l'image ; au runtime, Docker ne
remplace que le sous-dossier `logs` monté, `/app/tmp` lui-même garde la propriété baked dans
l'image. Pas de base de données envisagée (question posée par Steven) : ce fichier n'est
qu'un cache mémoïsé d'un scan filesystem, invalidé automatiquement par hash DVC — aucun besoin
de SQLite/Postgres/PVC pour ça (YAGNI), et PVC n'aurait de toute façon pas de sens hors
Kubernetes (Phase 3 non déployée).

**Vérifié en conteneur réel** : `docker compose build data-service` + recreate, `/app/tmp`
appartient bien à `appuser` après rebuild. Round-trip confirmé : premier appel
`?refresh=true` → 200 en 172,6s (scan complet), second appel → 200 en 0,56s,
`"cached":true`, fichier `/app/tmp/data_cache.json` bien présent sur disque. Non-régression :
26/26 tests verts, coverage 83,27 %, `ruff check` propre.

**Constat d'origine.** DVC n'est pas un serveur (pas de process qui écoute un port en continu) — c'est
un CLI, comme `git`. Il ne peut donc pas prendre la forme d'un conteneur autonome de la même
façon que `mlflow` (qui *est* un serveur). Ce que fait `data-service` — wrapper HTTP autour
du CLI `dvc` en `subprocess.run` (`GET /dvc/status`, `POST /dvc/pull`, `POST /dvc/push`,
`POST /dvc/repro`) — est la forme la plus sensée que peut prendre "DVC en service". `trainer`
a aussi `dvc[s3]` installé, mais uniquement parce que c'est là que `dvc repro` s'exécute
réellement (GPU requis pour les stages `train`/`train_segmentation`).

**Le problème qui a motivé le split** (même famille que le point 2) : `data-service` mélangeait
deux concerns — lecture/consultation (stats dataset, recherche, browsing d'images) et
opérations DVC (pull/push/repro — potentiellement longues, mutent l'état local). Résolu ci-
dessus.

## 4. `mlflow` — câblé, mais à sens unique ; la question du "où le ranger" mal posée au départ

**Résolu le 2026-08-28.** Le constat original ci-dessous ("`backend` ne lit jamais depuis
mlflow") était déjà obsolète avant même cette clôture — le code du flux retour (chargement
Model Registry avec fallback local, commit `5cdbaac`, 2026-08-27) existait, mais n'avait
**jamais été exercé avec succès** : aucun modèle n'était promu au stage `Production`, et deux
dépendances manquaient pour le rendre réellement fonctionnel. Trois correctifs, chacun
vérifié en conteneur réel :

1. **Promotion registry** : `covid_xray_cnn` v2 / `lung_segmentation_unet` v4 (noms hérités
   d'avant le commit `7468cc3` qui a aligné `params.yaml` sur `classification`/`segmentation`)
   re-enregistrés sous ces nouveaux noms via l'API MLflow (`create_model_version` pointant
   vers les mêmes artefacts, sans réentraînement), puis promus `Production`.
2. **`boto3` manquant** : `backend`/`segmentation-service` ne pouvaient pas télécharger les
   artefacts S3/MinIO du registry (`No module named 'botocore'`) — jamais détecté avant car
   aucun modèle n'avait jamais atteint le stage `Production`. Ajouté aux deux services
   (`boto3==1.43.82`, lockfile régénéré en conteneur Linux pour segmentation-service).
3. **`combined_loss` non désérialisable** : le U-Net utilise une loss custom non décorée
   `@keras.saving.register_keras_serializable()` — `mlflow.keras.load_model()` échouait à la
   compiler. Déjà contourné pour le chargement local (`compile=False`,
   `segmentation_service/model.py::_load_from_local_file`) mais pas pour le chargement
   registry — même fix appliqué (`load_model_kwargs={"compile": False}`), inutile pour
   l'inférence seule.

**Vérifié en conteneur réel** : `backend` et `segmentation-service` répondent tous les deux
`model_source: "registry"` sur `/health`. Non-régression : backend 88/88 tests (94,42 %),
segmentation-service 19/19 (94,95 %), `ruff check` propre sur les deux (un test unitaire mis à
jour pour refléter le nouvel argument `load_model_kwargs`).

**Constat d'origine (2026-08-26, obsolète — gardé pour traçabilité)** : le seul code Python
qui importait `mlflow` dans tout le repo était `trainer/scripts/train.py` et
`trainer/scripts/train_segmentation.py`. `backend` ne lisait jamais depuis mlflow — il
chargeait son modèle directement depuis un fichier `.keras` local, pas via le Model Registry.

**Ce que ça voulait dire** : mlflow était câblé en écriture (trainer y logue systématiquement)
et dispose d'une vraie infra dédiée (Postgres backend store, S3/MinIO artifact store, service
séparé port 5000) — ce n'était pas un vestige mort, mais sa valeur était purement
l'observation humaine via l'UI web, pas un maillon d'un flux automatisé.

**Sur "où ranger le Dockerfile"** — l'option "mlflow à la racine" évoquée en session avait
été retirée (mlflow n'a ni app ni code à lui, juste un Dockerfile de 14 lignes + un
`start.sh` — le déplacer n'aurait gagné que de la symétrie visuelle) ; sans objet maintenant
que le flux retour est résolu.

## Ordre suggéré

Les 4 points sont résolus (voir sections ci-dessus).

## Non traité ici

Les 4 points sont résolus (voir sections dédiées) — ce chantier est clos. Toute reprise future
(ex. nouvelle question d'architecture) repasse par la Validation humaine obligatoire
(CLAUDE.md) et une confirmation explicite du périmètre avant chaque étape.
