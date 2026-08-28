# CLAUDE.md — docker_covid (DS_COVID MLOps)

Industrialisation MLOps du pipeline DS_COVID : classification de radiographies pulmonaires
(COVID-19 · Lung Opacity · Normal · Viral Pneumonia). Repo GitHub **public** :
`Data-Team-DST/docker_covid`. Projet école (soutenance — voir § Calendrier).

---

## Contrat comportemental

**1 — Périmètre d'abord, action ensuite.**
Avant de commencer, énoncer les fichiers et services impactés. Si le périmètre touche plus d'un
service ou est ambigu → formuler ce qui va être touché et attendre confirmation.

**2 — Les frontières de service sont des lignes rouges.**
Zéro import Python direct entre `backend/`, `data-service/`, `log-service/`. Toute communication
inter-service passe par HTTP (`/health`, `/v1/...`, `/api/v1/...`). Si l'implémentation semble
demander une traversée de frontière autrement → STOP, proposer une alternative.

**3 — Zéro refactoring passant.**
Toucher uniquement ce qui est directement lié à la demande. Si un nettoyage est pertinent → le
signaler explicitement, jamais l'appliquer en silence.

**4 — "Done" = critères objectifs.**
Done = lint (`make lint`) propre + tests verts (`make test`) + coverage ≥ seuils (backend 80%,
data-service 80%) + aucune quality gate abaissée + `git status` propre.

**5 — Lire le code courant, jamais la mémoire.**
Avant toute affirmation sur un chemin, port, config ou fonction : lire le fichier. Ce CLAUDE.md
est un point de départ — le code en cours d'exécution est la seule source de vérité.

**6 — Tout ce qui est mis de côté doit être tracé et reproposé.**
Dès qu'une décision "je laisse ça de côté pour l'instant" est prise en cours de travail, la noter
explicitement et la reproposer à la fin de chaque réponse tant qu'elle n'est pas traitée ou
explicitement écartée par l'utilisateur.

**7 — Repo public : zéro fuite.** *(règle spécifique docker_covid)*
Avant tout commit ou push, grep les fichiers stagés pour toute référence interne, secret,
donnée personnelle ou identifiant réel (retour d'expérience : un résidu de projet précédent a
déjà fui dans des fichiers de règles avant d'être détecté ailleurs — même risque ici si un
fichier de config ou de notes est copié sans relecture). `.env` reste gitignoré en
permanence. `.claude/rules/`, `.claude/skills/`, `.claude/agents/` et `.claude/CLAUDE_AUDIT.md`
sont **volontairement publics** (transparence sur la configuration Claude Code de ce projet,
contenu relu avant chaque ajout) — le reste de `.claude/` (`settings.local.json`, `memory/`,
tout ce qui n'est pas explicitement exempté dans `.gitignore`) reste gitignoré en permanence.
Vérifier `git status` avant chaque push.

**8 — Toute réponse à l'utilisateur est en français.**

**9 — Valider en bac à sable, jamais en écrivant dans le repo réel.**
Toute vérification qui crée un venv, installe des dépendances ou exécute du code à titre de
test doit passer par une copie jetable (conteneur avec le repo monté en lecture seule + copie
dans l'espace du conteneur, ou tout sandbox équivalent), jamais en écrivant directement dans
les répertoires réels du repo. Retour d'expérience : une validation a partiellement écrasé un
`backend/.venv` réel préexistant en montant le repo en écriture directe dans un conteneur
Docker.

La copie doit lister explicitement les dossiers nécessaires (ex. `Makefile`, `pyproject.toml`,
`backend/`, `data-service/`, `ops/`…), jamais copier l'arbre complet avec des exclusions
(`tar --exclude=...`). Retour d'expérience : une copie par exclusion doit quand même parcourir
tout l'arbre pour décider quoi exclure — sur cette machine, les `.venv` locaux de chaque
service (backend/.venv, data-service/.venv, frontend/.venv, dashboard/.venv, chacun des
dizaines de milliers de petits fichiers) et `data/` (plusieurs Go) rendent ce parcours
extrêmement lent (plus de 10 minutes, bloqué). Une copie ciblée du même contenu utile a pris
quelques secondes.

**10 — Une erreur qui révèle un risque récurrent appelle une proposition de règle.**
Quand une erreur commise en session coûte du temps, risque une régression ou trompe
l'utilisateur (hypothèse fausse, vérification qui ne vérifie rien, effet de bord non anticipé)
— et que la cause n'est pas un simple faux pas ponctuel mais un risque qui peut se reproduire —
ne pas se contenter de corriger l'incident : proposer explicitement d'ajouter, modifier ou
supprimer une règle (CLAUDE.md ou `.claude/rules/`) pour empêcher la récidive. Proposition
seulement, jamais appliquée sans validation explicite de l'utilisateur — et pas systématique
pour chaque erreur mineure, sous peine de gonfler ce fichier de cas hyper-spécifiques.

---

## Validation humaine obligatoire

Avant toute action irréversible, **stopper et demander une confirmation explicite** :

- `git push`, `git pull`, `git merge`, `git reset`, `git rebase`
- Suppression de fichiers ou répertoires
- Opérations DVC destructives (`dvc gc`, force-push sur le remote MinIO)
- Modification de `.env`, credentials, clés API
- Déploiement (Kubernetes Phase 3, GHCR)
- Installation de paquets qui changent `requirements.txt`/`requirements-dev.txt` verrouillés

---

## Calendrier — à vérifier avant toute planification

D'après `README.md` (à recroiser avec l'état réel, ne pas prendre pour argent comptant) :

| Phase | Contenu | Deadline | Statut déclaré |
|---|---|---|---|
| 1 | Env reproductible, API, CI/CD | 13/03/2026 | Livré |
| 2 | Microservices, MLflow, DVC, log-service | 20/03/2026 | Livré |
| 3 | CI/CD complet, Kubernetes | 24/04/2026 | En cours (⚠️ deadline dépassée — à clarifier avec l'utilisateur) |
| 4 | Monitoring, Evidently, Drift | 01/09/2026 | À faire |
| **Soutenance** | Présentation finale | **04/09/2026** | À faire |

**US en attente** : US-11 (CI/CD deploy GHCR), US-16 (data augmentation).

⚠️ Si la date du jour est proche de la soutenance, **prioriser stabilité et sécurité sur
ambition** : pas de gros refactoring risqué à quelques jours de la démo. Confirmer l'urgence
réelle avec l'utilisateur avant toute action de nettoyage de grande ampleur.

---

## Architecture réelle

```
backend/                    FastAPI — port 8000 — inférence ML
├── Dockerfile                colocalisé mais contexte de build = racine du repo (pas backend/) :
                               COPY trainer/src ./src, requis par app/features/preprocessing.py
                               (réutilise ds_covid.preprocessing + ds_covid.segmentation pour un
                               preprocessing d'inférence identique à celui de l'entraînement)
├── app/main.py                point d'entrée
├── app/config.py               configuration centralisée
├── app/api/                    health.py, predict.py, security.py, metrics.py
├── app/models/loader.py        chargement modèle Keras
├── app/features/                preprocessing image — dépend de trainer/src/ds_covid (copié au
                                 build, pas d'import cross-service à l'exécution)
├── app/schemas/                  schémas Pydantic (réponses)
└── src/ml/                     baseline sklearn — utilisé uniquement par backend/tests/,
                                 hors périmètre de trainer/ (ne dépend pas de ds_covid)

data-service/                FastAPI — port 5001 — DVC pull/push/status, stats données
└── src/data_service/         main.py, api/v1/router.py

log-service/                 FastAPI — port 5002 — agrégateur logs JSON centralisé
frontend/                    Streamlit — port 8501 — multi-pages (01_accueil … 07_conclusion)
├── Dockerfile                colocalisé (contexte frontend/)
dashboard/                   Flask — port 5050 — backlog agile + data explorer
shared/                      logging_config.py — JSON structuré, importé par tous les services

trainer/                     Pipeline d'entraînement — service dédié (ex-scripts/ + backend/src/ds_covid/)
├── Dockerfile                colocalisé (contexte trainer/), image de base partagée avec frontend/
├── requirements.txt           extras trainer (mlflow, dvc[s3], jupyterlab, albumentations…)
├── src/ds_covid/               augmentation.py, features.py, models.py, preprocessing.py,
                                 segmentation.py (U-Net poumons), data.py (MemmapSequence)…
                                 réutilisé par backend/ au build (COPY trainer/src, pas d'import
                                 Python cross-service — voir backend/Dockerfile ci-dessus)
└── scripts/                    preprocess.py, train.py, evaluate.py, augment.py +
                                 preprocess_segmentation.py, train_segmentation.py,
                                 evaluate_segmentation.py (stages DVC)

infrastructure/
├── docker/                  Dockerfiles restants : mlflow, base (backend/frontend/trainer colocalisés)
└── docker-compose.yml        stack complète (backend, data-service, dvc-service, streamlit,
                               trainer, mlflow, log-service, postgres, minio, minio-init).
                               `dashboard` (Flask) n'est pas dans ce compose, lancé à part.

kubernetes/                  manifests K8s (Phase 3, non déployé) — racine, hors infrastructure/
ops/                          setup.sh, check_quality.sh, fix_style.sh, start_local.sh
                               (ex-infrastructure/scripts/, renommé pour éviter la collision
                               avec scripts/load_test/)

scripts/load_test/           Locust — test de charge sur /predict
data/raw.dvc                 42 330 images, versionné DVC (806 MB), remote MinIO
dvc.yaml / params.yaml       Pipeline reproductible (dvc repro) — stages dans trainer/scripts/
```

**Isolation de service** : `backend/.venv` et `data-service/.venv` sont deux venvs distincts
(`make setup-be` / `make setup-ds`). Ne jamais faire dépendre l'un de l'autre en Python direct.

---

## Stack & conventions

- **Python** 3.11+, PEP 8, type hints
- **API** : FastAPI (backend, data-service, log-service) + Pydantic — Flask pour dashboard
  (services simples, pas de couche service/router séparée à ce jour)
- **ML** : TensorFlow/Keras (CNN, base InceptionV3), preprocessing image 256×256
- **Tests** : pytest — coverage ≥ 80% backend, ≥ 80% data-service (`make test`, `make test-be`,
  `make test-ds`)
- **Lint** : ruff + pylint (`make lint`, `make lint-full`, `make fix` pour auto-correction)
- **Data versioning** : DVC, remote MinIO (`make dvc-setup`, `make dvc-push`, `make dvc-pull`)
- **ML tracking** : MLflow (port 5000) + Postgres (backend MLflow) + MinIO (artifacts)
- **Containers** : Docker par service + `infrastructure/docker-compose.yml` (stack complète)
- **CI/CD** : `.github/workflows/cicd.yml` — lint → tests → build GHCR
- **Secrets** : uniquement via `.env` (jamais commité — voir règle #7)

---

## Qualité — seuils à ne jamais abaisser

- Coverage : backend ≥ 80%, data-service ≥ 80% (`--cov-fail-under`)
- `ruff check` + `pylint` sans erreur bloquante (`make lint-full`)
- `verify=False` dans les appels HTTP : **interdit**
- `# noqa` / `# type: ignore` en masse : **interdit**
- Secrets/`.env`/`.claude/` : jamais trackés par git (vérifier `.gitignore` avant tout ajout de fichier sensible)

---

## Skills utiles pour ce projet

Un sous-ensemble ciblé est fourni dans `.claude/skills/` :

| Quand | Skill |
|---|---|
| API FastAPI (backend, data-service) | `/fastapi-patterns` |
| Docker / docker-compose (stack multi-services) | `/docker-patterns` |
| Tests pytest, coverage | `/python-testing` |
| Code Python général | `/python-patterns` |
| Pipeline ML, DVC, MLflow, reproductibilité | `/mle-workflow` |
| Postgres (backend MLflow) | `/postgres-patterns` |
| Revue sécurité (repo public !) | `/security-review` |
| CI/CD, déploiement, rollback | `/deployment-patterns` |
| Migrations de schéma (si Postgres évolue) | `/database-migrations` |

---

## Modes opératoires

@.claude/CLAUDE_AUDIT.md
