# Nettoyage — dette technique différée

Issu de l'audit du 2026-08-24 (branche `chore/claude-code-setup`). Ces points ne sont **pas
bloquants** pour la soutenance du 04/09/2026 — à traiter après, dans l'ordre qui convient.
Ne pas corriger en masse cette semaine (voir CLAUDE.md § Calendrier).

## Déjà fait
- [x] `infrastructure/scripts/dvc_security_demo.sh`, `infrastructure/scripts/log_dataset_mlflow.py`
      et `infrastructure/scripts/check_quality.sh` : anonymisation de toutes les références à un
      projet client tiers réel (nom du client, nom de dataset, nom d'environnement d'hébergement)
      trouvées dans les commentaires, bannières, noms de run MLflow et tags. Les scripts sont
      conservés (fonctionnalité et structure inchangées) — seules les chaînes identifiantes ont
      été remplacées par des termes génériques. Ces scripts restent orphelins (aucune référence
      Makefile/README/CI) et `dvc_security_demo.sh`/`log_dataset_mlflow.py` pointent toujours vers
      `data-service/data/` (inexistant dans ce repo, le vrai dossier est `data/`) — non corrigé,
      hors périmètre de cette demande.
- [x] `test.ipynb` — les 5 occurrences du chemin local `/home/cepa/DST/docker_covid/...` (sorties
      de cellules + source de la cellule `d4cf4d7c`) remplacées par des chemins relatifs
      (`data/raw/...`), en édition texte directe pour ne pas ré-exécuter/reformater le notebook.
      JSON revalidé après coup.
- [x] `backend/src/ds_covid/__init__.py:8,17` — email personnel réel
      (`rafael.cepa@cnrs-orleans.fr`) remplacé par `rafael.cepa@example.fr`, aligné sur
      `backend/src/__init__.py` qui utilisait déjà ce format. Ligne d'auteur (`- Rafael Cepa
      <email>`) simplifiée pour retirer l'email du docstring aussi.
- [x] `infrastructure/kubernetes/configmap.yaml:23,25` — `MINIO_ROOT_PASSWORD` et
      `POSTGRES_PASSWORD` vidés (`""`, avec commentaire "Définir en prod"), même traitement que
      `API_KEY` déjà présent. Les identifiants non sensibles (usernames, nom de DB) restent en
      place — pas de refonte vers Secret opaque/sealed-secret, manifests Phase 3 non déployés.
- [x] `frontend/requirements.txt` — `mlflow`, `opencv-python`, `scikit-image` retirés (aucun
      import trouvé dans `frontend/`).
- [x] `data-service/requirements.txt:6` — `httpx` retiré du fichier de prod (reste dans
      `dev-requirements.txt`, seul endroit où il est réellement utilisé, en test).
- [x] CI (`cicd.yml`, 3 jobs lint) — `ruff`/`pylint` désormais pinnés (`ruff==0.8.6`,
      `pylint==3.3.9`), et `data-service/dev-requirements.txt` aligné sur le même `ruff==0.8.6`
      (remplace `ruff>=0.4.0`). Versions validées avant application : `ruff==0.8.6` passe sans
      erreur sur `backend/app/`, `data-service/src/` et `frontend/` (testé dans un venv temporaire
      isolé). `pylint==3.3.9` conservé en dessous de la 4.x pour éviter un saut de version majeure
      non testé ; le job pylint reste de toute façon non bloquant (`|| true` déjà présent dans
      `cicd.yml`, pré-existant, hors périmètre).
- [x] `docs/plan_de_base.txt` — tracké par git malgré la règle `.gitignore:72 plan_de_base.txt`
      (footgun classique : fichier indexé avant l'ajout de la règle, donc pas déignoré
      rétroactivement). Contenu vérifié avant action : un schéma d'archi texte, rien de sensible.
      Untracké via `git rm --cached` (fichier conservé sur disque, la règle s'applique désormais).
      Trouvaille remontée par une session Claude Code parallèle explorant ce même repo.
- [x] `data-service/tests/` — 22 tests ajoutés (`data-service/tests/test_router.py`) : couvrent
      `/v1/data/image` (dataset invalide, path manquant, path traversal, 404, succès),
      `/v1/data/search` (dataset invalide, query manquante, dossier absent, scan fallback),
      les 5 endpoints DVC (`status`, `remotes`, `pull`, `push`, `repro` — succès + échecs, via
      mock de `subprocess.run`, pas de dépendance à un vrai binaire `dvc`), et le cache de
      `/v1/data/stats` (refresh + hit). Couverture `router.py` : 38% → 83%, couverture globale
      data-service : 44% → 83%. Lint (`ruff==0.8.6`) et 24 tests (2 existants + 22 nouveaux)
      validés dans un venv isolé avant application.
- [x] `infrastructure/scripts/dvc_security_demo.sh` et `infrastructure/scripts/log_dataset_mlflow.py`
      — supprimés (chantier `CHANTIER_INFRA.md`, 2026-08-26). Orphelins confirmés (aucune
      référence Makefile/README/CI) et logique entièrement liée à un autre projet (dossier
      `data-service/data/` inexistant ici, types de fichiers `.docx/.pdf/.xlsx/.pptx`, remote DVC
      local `/home/*` au lieu de MinIO S3) — adapter aurait signifié réécrire, pas corriger.
      Referme le point resté ouvert dans l'entrée précédente ("hors périmètre").
- [x] `infrastructure/docker/base/requirements.txt` et `infrastructure/docker/trainer/requirements.txt`
      — verrouillés via `pip-compile --generate-hashes` (chantier `CHANTIER_INFRA.md`, 2026-08-26),
      seule zone du repo encore non verrouillée. `.in` ajoutés à côté de chaque `.txt`. Compilé en
      Python 3.11 (même version que les autres lock files du repo) dans un venv jetable WSL Ubuntu
      — jamais sur cette machine Windows (voir piège `pip-compile` déjà documenté en mémoire projet)
      et jamais en écrivant dans le repo réel (CLAUDE.md règle #9). Versions déjà pinnées ailleurs
      réutilisées pour cohérence : `numpy==2.0.2`, `scikit-learn==1.5.2`, `pillow==11.0.0` (comme
      `backend/requirements.txt`), `mlflow==2.19.0` (comme `infrastructure/docker/mlflow/Dockerfile`).
- [x] CI (`cicd.yml:117,156,203-204`) — `pip install -r requirements*.txt` passe désormais par
      `--require-hashes`. Lock files générés avec `pip-compile --generate-hashes` pour
      `backend/requirements-dev.txt`, `frontend/requirements.txt` et
      `data-service/{requirements,dev-requirements}.txt` (ce dernier compilé avec `-c
      requirements.txt` pour garder les dépendances transitives partagées cohérentes entre les
      deux fichiers installés ensemble en CI). Fichiers `.in` ajoutés à côté de chaque `.txt`
      comme source de vérité pour une future regénération (`pip-compile --generate-hashes
      --output-file=X.txt X.in`, `--allow-unsafe` nécessaire pour data-service à cause de
      `setuptools` tiré transitivement par `dvc` → `zc-lockfile`).
      Versions déjà pinnées en dur (`fastapi==0.115.6`, `numpy==2.0.2`, `streamlit==1.41.1`...)
      inchangées ; celles qui étaient en `>=`/non-pinnées ont été résolues à la dernière version
      disponible (notable : `kagglehub` → 1.0.2, `plotly` → 6.9.0, tout le pipeline `dvc[s3]`
      pour data-service). Chaque lock file validé avant application : `pip install
      --require-hashes` propre dans un venv isolé + suite de tests complète rejouée dessus
      (backend : 57 tests, 78% coverage ; data-service : 24 tests, 83% coverage, prod+dev
      installés ensemble comme en CI ; frontend : import de tous les paquets top-level).
