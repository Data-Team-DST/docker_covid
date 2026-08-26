# Chantier — Réorganisation structurelle (Dockerfiles, kubernetes/, scripts/)

Ouvert le 2026-08-26, à traiter **après la soutenance du 04/09/2026** (CLAUDE.md § Calendrier :
pas de refactoring structurel risqué à quelques jours de la démo). Constat seul — aucune
modification appliquée. Origine : questions posées par Steven en session sur la cohérence de
placement des Dockerfiles, de `kubernetes/`, et des deux dossiers `scripts/`.

## Constat

### 1. Placement des Dockerfile — déjà incohérent dans le repo actuel

Deux conventions coexistent aujourd'hui dans `infrastructure/docker-compose.yml` :

- **Colocalisé dans le service** : `data-service/Dockerfile` (`context: ./data-service`),
  `log-service/Dockerfile` (`context: ./log-service`).
- **Centralisé sous `infrastructure/docker/`** : `backend` → `infrastructure/docker/backend/Dockerfile`,
  `streamlit` → `infrastructure/${STREAMLIT_DOCKERFILE}`, `trainer` →
  `infrastructure/${TRAINER_DOCKERFILE}`, `mlflow` → `infrastructure/docker/mlflow/Dockerfile`
  (contexte `.` dans les quatre cas).

**Piste** : aligner sur la convention colocalisée (majoritaire à 2 services sur 4 "vrais"
services applicatifs) — `backend/Dockerfile`, `frontend/Dockerfile` (streamlit). Ne s'applique
pas proprement à `trainer` et `mlflow`, qui ne sont pas des services au même sens (voir #4).

### 2. `kubernetes/` sous `infrastructure/` vs racine

Pas d'argument technique fort dans un sens ou l'autre — question de convention. Aujourd'hui
`infrastructure/` regroupe tout l'IaC (docker, kubernetes, scripts). Un `kubernetes/` (ou `k8s/`)
à la racine est un pattern courant ailleurs mais n'est pas objectivement supérieur ici.

**Piste** : à trancher par préférence, faible priorité. Impact limité (manifests + éventuelles
références CI à vérifier — `.github/workflows/`).

### 3. `infrastructure/scripts/` — pas homogène bash, et collision de nom avec `scripts/` racine

Contenu réel de `infrastructure/scripts/` : `fix_style.sh`, `start_local.sh`,
`start_services.sh`, `check_requirements.sh`, `setup.sh`, `check_quality.sh` (bash) **+**
`check_code_smell_parser.py` (Python, appelé par `check_quality.sh` via `exec`). Pas 100% bash.

Le dossier `scripts/` existe déjà à la racine — pipeline DVC (`preprocess.py`, `train.py`,
`evaluate.py`, `augment.py`). Déplacer `infrastructure/scripts/*` vers la racine tel quel
créerait une collision de nom/domaine (tooling ops vs pipeline ML) — nécessite un nom différent
si déplacé (ex. `tools/`, `ops/`), pas juste un `mv` vers `scripts/`.

**Piste** : dépend de la décision sur #4. Si `scripts/` racine devient un service `trainer/`
dédié, le nom `scripts/` racine se libère et `infrastructure/scripts/` pourrait le récupérer
sans collision — mais ce n'est pas une raison suffisante de le faire dans l'urgence.

### 4. `scripts/` racine — pipeline DVC déjà couplé à `backend/src/`, candidat à devenir un service dédié

`scripts/{preprocess,train,evaluate,augment}.py` font chacun `sys.path.insert(0,
str(PROJECT_ROOT / "backend" / "src"))` puis importent `from ds_covid.xxx import ...` — un
couplage cross-dossier qui ressemble à ce que la règle R8 (zéro import Python direct entre
services) interdit entre microservices, sauf que `scripts/` n'a jamais été déclaré comme
service à part entière donc R8 ne s'applique pas formellement.

`dvc.yaml` référence ces scripts + les modules `backend/src/ds_covid/*.py` comme `deps` de
chaque stage. Le service `trainer` du compose n'a pas de dossier propre : son Dockerfile fait
`COPY backend/src/ /workspace/src/`, et le compose monte `./backend/src:/app/src` — `trainer`
est aujourd'hui une coquille Docker qui exécute du code emprunté à `backend/` et `scripts/`
racine, pas un service autonome au sens des autres.

**Piste** : extraire `backend/src/ds_covid/` + `scripts/*.py` vers un vrai dossier `trainer/`
(ou équivalent) avec son propre `requirements.txt`, entry point, et Dockerfile colocalisé —
formaliserait ce qui existe déjà de fait. Impact large : `dvc.yaml` (tous les stages),
`infrastructure/docker/trainer/Dockerfile`, `docker-compose.yml` (volumes trainer), CI si elle
touche ces chemins. Le point le plus structurant des quatre — les trois autres en dépendent
partiellement (#1 et #3 se résolvent plus proprement une fois #4 tranché).

## Ordre suggéré (à confirmer avec Steven le moment venu)

1. #4 d'abord (le plus structurant, débloque #1 et #3)
2. #1 ensuite (Dockerfiles colocalisés, une fois `trainer/` existant)
3. #3 (renommage/déplacement `infrastructure/scripts/`)
4. #2 en dernier (kubernetes/, indépendant, faible enjeu)

## Non traité ici

Aucune action prise — audit seul, comme `CHANTIER_INFRA.md`. Toute correction repasse par la
Validation humaine obligatoire (CLAUDE.md) et une confirmation explicite du périmètre avant
chaque étape, une fois la soutenance du 04/09/2026 passée.
