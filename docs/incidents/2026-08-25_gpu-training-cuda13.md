# Incident — `dvc repro` GPU cassé sur driver CUDA 13.1 (2026-08-25)

Session d'une après-midi, branche `raf5`. Point de départ : « je vais lancer `dvc repro`
sans GPU ça va être la guerre ». Huit problèmes indépendants, empilés les uns sur les
autres, avant d'obtenir un pipeline d'entraînement GPU réellement fonctionnel de bout
en bout (training + tracking MLflow inclus).

## Résumé pour qui n'a pas le temps de tout lire

- `make dvc-repro` fonctionne maintenant en GPU réel sur la RTX 3060, training **et**
  tracking MLflow inclus (validé par un smoke test complet : `log_model` +
  `log_metrics` jusqu'au bout, modèle réellement uploadé sur MinIO).
- Ça a nécessité de monter TensorFlow **2.18 → 2.21** dans l'image de base partagée
  (`infrastructure/docker/base/Dockerfile`), ce qui **casse `streamlit`**
  (`protobuf` incompatible — voir § Dette ci-dessous). Accepté explicitement : cette
  branche n'est pas la branche de démo.
- Ça a aussi nécessité de monter le serveur MLflow **2.19.0 → 3.15.1** (§ 5), avec sa
  propre cascade de 4 sous-problèmes (API manquante, crash-loop mémoire, sécurité
  DNS-rebinding, credentials S3 côté client).
- Aucune image n'a été poussée sur GHCR — le fix ne vit que dans les Dockerfiles/commits,
  pas encore rebuild côté CI/registre.

## Chronologie

### 1. `class_weight` + `Sequence` custom casse sous Keras 3

Premier run réel du stage `train` (jusque-là jamais atteint) : crash immédiat.

```
ValueError: The two structures don't have the same sequence length.
Input structure has length 2, while shallow structure has length 3.
```

`scripts/train.py` passait `class_weight=` à `model.fit()` avec un `Sequence` custom
(`MemmapSequence`, qui renvoie `(X, y)`). Keras 3 (embarqué par TF 2.18+) tente de
zipper un `sample_weight` en interne dans ce cas et casse sur un générateur qui n'a que
2 éléments. `train_segmentation.py` n'était pas concerné (pas de `class_weight`).

**Fix** : `backend/src/ds_covid/data.py` — `MemmapSequence` calcule le `sample_weight`
lui-même et renvoie un 3-tuple si un `class_weight` lui est passé en paramètre, au lieu
de passer par l'argument `class_weight` de `fit()`. Le split validation reste non
pondéré (`class_weight` ne doit affecter que la loss d'entraînement, pas `val_loss`
surveillée par `EarlyStopping`).

### 2. GPU non utilisé — driver stub au lieu du vrai driver

Le training tournait (15s/batch, ~43 min/epoch) mais entièrement en CPU :

```
cuda_driver.cc:152] failed call to cuInit: CUDA_ERROR_NOT_FOUND: named symbol not found
```

`nvidia-smi` fonctionnait dans le container (NVML, mécanisme séparé) — piège classique,
ça donne une fausse impression que le GPU passe. Diagnostic : `/usr/lib/x86_64-linux-gnu/libcuda.so.1`
dans le container ne fait que 175 Ko (un stub de compilation), alors que le vrai driver
WSL2 (25 Mo, matching le driver Windows 591.86) existe bien sur la machine, mais sous
`/usr/lib/wsl/drivers/<hash>.inf_amd64_.../libcuda.so.1.1` — jamais monté/symlinké à
l'emplacement standard `/usr/lib/wsl/lib/` que Docker Desktop est censé préparer.

Testé et écarté avant de trouver la vraie cause : redémarrer Docker Desktop, mise à jour
majeure du moteur (24.0.6 → 29.7.2), `wsl --update`, reboot Windows complet — **aucun
n'a suffi**. La cause profonde était un bug de mapping WSL2/Docker Desktop sur cette
machine, pas un état transitoire.

**Fix** : `infrastructure/docker/trainer/gpu-entrypoint.sh` — script d'entrypoint qui
détecte le dossier driver réel (`/usr/lib/wsl/drivers/*.inf_amd64_*/`) au démarrage du
container et symlink manuellement `libcuda.so.1`, `libnvidia-ml.so.1`,
`libnvidia-ptxjitcompiler.so.1`, `libnvdxgdmal.so.1` vers `/usr/lib/wsl/lib/`, avant
d'exécuter la vraie commande. No-op sur Linux natif avec `nvidia-container-toolkit`
(le dossier `/usr/lib/wsl/` n'existe pas), donc sans risque de casser un déploiement CI
ou une autre machine.

Validé pas à pas via `ctypes` direct (`cuInit` → 0, `cuDeviceGetCount` → 1 device) avant
de faire confiance à TensorFlow — utile, car l'étape suivante a montré que TF lui-même
avait un problème séparé malgré un driver qui fonctionnait parfaitement en direct.

### 3. TensorFlow 2.18 incompatible avec le driver CUDA 13.1

Même avec le driver correctement monté, `tf.config.list_physical_devices('GPU')`
renvoyait `[]` avec `CUDNN_STATUS_INTERNAL_ERROR`. Cause : le driver NVIDIA de la
machine est très récent (591.86, `nvidia-smi` annonce CUDA 13.1) — un saut de version
majeure au-delà de ce que TF 2.18 (compilé pour CUDA 12.3) et surtout **l'image
officielle `tensorflow/tensorflow:*-gpu`** savent gérer : elle embarque encore un cuDNN
apt 8.9.6, alors que le binaire TF attend du cuDNN 9.x.

**Fix** :
- `infrastructure/docker/base/Dockerfile` — `tensorflow/tensorflow:2.18.0-gpu` →
  `2.21.0-gpu`.
- `infrastructure/docker/trainer/requirements.txt` — ajout de `nvidia-cudnn-cu12`,
  `nvidia-cublas-cu12`, `nvidia-cufft-cu12` (mécanisme pip que TF 2.19+ attend
  réellement ; trouvé automatiquement par TF via son propre RPATH, sans réglage
  `LD_LIBRARY_PATH` supplémentaire pour ces libs-là — seul `libcuda.so.1`, le driver,
  a besoin du symlink manuel du point 2, car lui ne peut pas être fourni par pip).
- `protobuf` repin `<6,>=5.0` → `<7,>=6.31.1` (TF 2.21 exige `>=6.31.1`, incompatible
  avec l'ancien pin).

Validé par un entraînement réel (pas juste la détection) : `build_cnn` +
`MemmapSequence` + `TqdmCallback`, 1 epoch sur données synthétiques, GPU confirmé
utilisé (`StreamExecutor ... NVIDIA GeForce RTX 3060 ... compute capability 8.6`).

### 4. Effet de bord : `streamlit` cassé

`infrastructure/docker/base/Dockerfile` est **partagé** entre `trainer` et
`frontend/streamlit`. Le bump protobuf casse `streamlit==1.41.1`, qui exige
`protobuf<6` en dur. Pour réconcilier, il aurait fallu monter `streamlit` vers `1.62.0`
(~20 versions mineures) — jugé trop risqué à 10 jours de la soutenance (voir CLAUDE.md
§ Calendrier) pour un service qui n'est pas sur la branche de démo.

**Décision assumée** : ne pas toucher à `frontend/requirements.txt`. `streamlit` reste
cassé sur `raf5` tant que cette branche n'est pas celle utilisée pour la démo.

### 5. Corruption silencieuse de `train.py` par un merge Git

Entre deux relances, un `git pull` (VS Code) a fusionné 47 commits d'`origin/raf5`.
Le merge de `scripts/train.py` n'a montré **aucun conflit textuel** — mais a réintroduit
une ancienne définition locale de `class MemmapSequence` (sans `class_weight`, héritée
d'une version d'`origin` antérieure au refactor vers `ds_covid/data.py`) **en plus** de
`from ds_covid.data import MemmapSequence`. Comme la classe locale est définie *après*
l'import, elle écrase silencieusement le nom importé au chargement du module — Git n'a
rien à signaler puisque les deux blocs ne se chevauchent pas ligne à ligne, mais le
résultat est sémantiquement cassé (`TypeError: unexpected keyword argument
'class_weight'` au premier `dvc repro` réel post-merge).

**Fix** : suppression de la classe locale dupliquée, l'import `ds_covid.data` reste seul
en vigueur. Aucun autre fichier touché par ce merge (`data.py`, `models.py`,
`segmentation.py`, `train_segmentation.py`) n'avait ce problème — vérifié un par un.

**Leçon** : après tout merge Git qui touche un fichier qu'on vient de corriger, relire
le fichier (pas juste vérifier l'absence de marqueurs de conflit) avant de relancer.

### 6. Serveur MLflow 2.19.0 incompatible avec le client 3.15.1

Une fois `train` fonctionnel en GPU, il plante à l'étape `mlflow.keras.log_model()` :
404 sur `/api/2.0/mlflow/logged-models`, une API introduite par MLflow 3.x et absente
du serveur (`infrastructure/docker/mlflow/Dockerfile`, resté épinglé `mlflow==2.19.0`).
Le client (dans `trainer/requirements.txt`, `mlflow` non pinné) avait résolu en
`3.15.1` — un vrai décalage client/serveur, pas juste un manque de pin.

Repin le client à `2.19.0` pour matcher le serveur ? Non viable : `mlflow-skinny==2.19.0`
exige `protobuf<6`, en conflit direct avec TF 2.21 (`>=6.31.1`, § 3) — ça rouvrirait la
guerre protobuf déjà réglée. Il fallait donc monter le **serveur**, pas redescendre le
client. `mlflow-server` n'a aucun autre consommateur dans le repo (rien dans `backend/`
ni `dashboard/`), et `start.sh` fait déjà un `mlflow db upgrade` automatique — risque
contenu, contrairement au cas streamlit.

**Fix** : `infrastructure/docker/mlflow/Dockerfile` — `mlflow==2.19.0` → `3.15.1`. Puis
trois sous-problèmes trouvés en cascade, chacun diagnostiqué et corrigé avant que le
smoke test (`log_model` + `log_metrics` réels) passe :

- **Crash-loop mémoire silencieux** — aucune erreur dans les logs, juste des processus
  enfants qui meurent en boucle (`docker stats` a montré 511.8/512 Mo, 99.97%). Le
  nouveau serveur FastAPI/Uvicorn de MLflow 3 lance un `job_runner` + plusieurs
  consommateurs `huey` (nouvelle file de tâches interne asynchrone), dépassant la limite
  mémoire taillée pour l'ancien serveur Flask. Fix : `deploy.resources.limits.memory`
  512m → 2g dans `docker-compose.yml`, + `--workers 1` dans `start.sh` (le service n'a
  que `cpus: "0.5"`, plusieurs workers web n'apportent rien).
- **403 "Invalid Host header — possible DNS rebinding attack detected"** — nouvelle
  protection de sécurité MLflow 3, n'autorise par défaut que `localhost`/IPs privées ;
  refuse le nom de service Docker `mlflow` utilisé par le trainer. Fix : `--allowed-hosts
  "mlflow:*,localhost:*"` dans `start.sh` — le wildcard `:*` est nécessaire, une liste
  personnalisée sans lui a cassé jusqu'au healthcheck interne (`Host: localhost:5000`
  ne matchait plus un simple `localhost` sans port).
- **`ModuleNotFoundError: boto3` puis `NoCredentialsError`** — MLflow 3 fait l'upload
  des artefacts modèle **côté client** (boto3 direct) au lieu de le proxifier via le
  serveur. Fix : `boto3` ajouté à `trainer/requirements.txt` + mêmes credentials MinIO
  (`MLFLOW_S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
  `AWS_DEFAULT_REGION`) que le service `mlflow` déjà présents, répliqués sur le service
  `trainer` dans `docker-compose.yml`.

## État actuel

- `make dvc-repro` tourne en GPU réel, training **et** tracking MLflow inclus.
- Commit `8fd4706` (branche `raf5`) : bump serveur MLflow + fixes mémoire/sécurité/S3.
- Commit `dbe7415` : suppression de la classe `MemmapSequence` dupliquée (§ 5).
- Commit `d501356` (branche `raf5`) : `base/Dockerfile`, `trainer/Dockerfile`,
  `trainer/requirements.txt`, nouveau `trainer/gpu-entrypoint.sh`.
- Commit antérieur `977a5eb` : fix `class_weight`/Keras 3, `tqdm` sur `train.py` et
  `train_segmentation.py`, cible Makefile `dvc-repro`.

## Dette / points ouverts

- **`streamlit` cassé** sur cette branche (protobuf). À traiter si/quand `raf5` doit
  redevenir une branche de démo, ou si le frontend doit être testé — bump vers
  `streamlit>=1.62.0` + régénération complète du lock file `frontend/requirements.txt`
  (pip-compile, en conteneur Linux).
- **Image de base non poussée sur GHCR** — le fix ne vit que dans les Dockerfiles commit-és
  et dans le cache Docker local de cette machine (image retaguée manuellement en
  `ghcr.io/data-team-dst/covid-xray-base:latest` pour que `docker compose --build` la
  retrouve sans repull). Sur une autre machine ou après un `docker system prune`, le
  premier `make dvc-repro` re-déclenchera un vrai rebuild depuis le Dockerfile (normal,
  pas de risque de régression, juste plus long au premier lancement).
- Le workaround `gpu-entrypoint.sh` est spécifique à un bug Docker Desktop/WSL2 sur
  cette machine (Docker Desktop très en retard avant cette session — moteur 24.0.6,
  mis à jour en 29.7.2 pendant cette même session). À réévaluer si une future mise à
  jour Docker Desktop corrige le montage natif — le script est un no-op inoffensif
  sinon (pas besoin de le retirer préventivement).
- Une expérience/modèle `smoke-test` / `smoke-test-model` traîne dans le tracking MLflow
  (créée pour valider le fix § 6) — sans conséquence (instance de dev), à supprimer via
  l'UI MLflow si ça gêne visuellement, pas urgent.
- Le comportement mémoire du nouveau serveur MLflow 3 (job runner + consommateurs huey)
  n'a été observé que sur un seul run de smoke test ; `2g` donne de la marge (~1.5 Go
  observé en pointe) mais n'a pas été stress-testé sur un entraînement complet avec
  plusieurs runs concurrents — à surveiller (`docker stats mlflow-server`) si le service
  redevient instable en usage réel.
