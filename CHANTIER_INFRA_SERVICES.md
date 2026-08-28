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
- **Non fait** : 03 (captures d'écran statiques — env Windows/WSL/Colab, masking, augmentation ;
  faible priorité, coût faible si repris plus tard). 06 (CI/CD) — **volontairement pas migré**,
  contenu périmé (présente Docker/CD/monitoring comme absents alors qu'ils existent).
- `frontend/` (Streamlit) devient supprimable une fois 03 traité ou explicitement abandonné.

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

**Constat.** DVC n'est pas un serveur (pas de process qui écoute un port en continu) — c'est
un CLI, comme `git`. Il ne peut donc pas prendre la forme d'un conteneur autonome de la même
façon que `mlflow` (qui *est* un serveur). Ce que fait `data-service` — wrapper HTTP autour
du CLI `dvc` en `subprocess.run` (`GET /dvc/status`, `POST /dvc/pull`, `POST /dvc/push`,
`POST /dvc/repro`) — est la forme la plus sensée que peut prendre "DVC en service". `trainer`
a aussi `dvc[s3]` installé, mais uniquement parce que c'est là que `dvc repro` s'exécute
réellement (GPU requis pour les stages `train`/`train_segmentation`).

**Le problème** (même famille que le point 2) : `data-service` mélange deux concerns —
lecture/consultation (stats dataset, recherche, browsing d'images) et opérations DVC
(pull/push/repro — potentiellement longues, mutent l'état local). Ce n'est pas la même
"masse" de mélange que `dashboard` (moins visible, pas de UI produit dedans), mais le
principe est identique.

**Piste** : scinder en `data-service` (lecture seule : stats, recherche, images) et un
service séparé (`pipeline-service` ou `dvc-service`) pour les opérations DVC — **si ça vaut
le coût d'un conteneur de plus** pour un projet école. Pas évident que ce soit prioritaire ;
à soupeser avec le point 2 (est-ce qu'on multiplie les microservices pour la pureté
architecturale, ou est-ce qu'on accepte un mélange raisonnable dans un service utilitaire
interne ?).

## 4. `mlflow` — câblé, mais à sens unique ; la question du "où le ranger" mal posée au départ

**Constat vérifié le 2026-08-26** : le seul code Python qui importe `mlflow` dans tout le
repo est `trainer/scripts/train.py` et `trainer/scripts/train_segmentation.py` (`import
mlflow`, `mlflow.set_tracking_uri`, `mlflow.start_run`, `mlflow.log_params/metrics`,
`mlflow.keras.log_model`). **`backend` ne lit jamais depuis mlflow** — il charge son modèle
directement depuis un fichier `.keras` local (`backend/app/config.py:
model_path = "data/models/best_model.keras"`), pas via le Model Registry mlflow.

**Ce que ça veut dire** : mlflow est câblé en écriture (trainer y logue systématiquement) et
dispose d'une vraie infra dédiée (Postgres backend store, S3/MinIO artifact store, service
séparé port 5000) — ce n'est pas un vestige mort. Mais sa valeur aujourd'hui est purement
l'observation humaine via l'UI web, pas un maillon d'un flux automatisé (rien ne "pull" le
meilleur modèle du registry pour le déployer, par exemple). C'est cohérent avec un stade de
maturité MLOps donné (Phase 4 du calendrier — Monitoring/Evidently/Drift — pas encore
atteinte), pas une erreur en soi.

**Sur "où ranger le Dockerfile"** — l'option "mlflow à la racine" évoquée en session est
retirée (mlflow n'a ni app ni code à lui, juste un Dockerfile de 14 lignes + un `start.sh` —
le déplacer ne gagnerait que de la symétrie visuelle). La vraie question, si elle doit être
retravaillée, n'est pas "dans quel dossier" mais "est-ce que mlflow doit rester write-only
(trainer logue, personne ne lit) ou est-ce qu'on câble un vrai flux retour (ex: backend/
data-service interroge le Model Registry pour savoir quel modèle est `Production`, au lieu
d'un chemin de fichier codé en dur)" — ça, c'est un vrai sujet MLOps, pas un sujet de
rangement de dossier.

## Ordre suggéré (à confirmer avec Steven une fois la soutenance passée)

1. **Point 4 (mlflow)** — clarifier d'abord l'intention : reste-t-il un outil d'observation
   pure, ou veut-on un vrai flux retour (registry → déploiement) ? Ça conditionne si ça vaut
   la peine d'y toucher du tout.
2. **Point 1 (base)** — le plus mécanique des quatre une fois le point 2 tranché (si
   `frontend` disparaît au profit de `dashboard`/`demonstration`, la question "frontend a-t-il
   besoin de GPU" devient sans objet différemment).
3. **Point 2 (frontend/dashboard)** — le plus gros chantier, nécessite l'inventaire page par
   page avant toute décision de structure.
4. **Point 3 (DVC/data-service)** — indépendant des trois autres, priorité la plus faible
   (le split n'est pas évident d'être rentable pour la taille du projet).

## Non traité ici

Aucune action prise — audit et options seulement, comme `CHANTIER_ARCHITECTURE.md`. Toute
correction repasse par la Validation humaine obligatoire (CLAUDE.md) et une confirmation
explicite du périmètre avant chaque étape, une fois la soutenance du 04/09/2026 passée.
