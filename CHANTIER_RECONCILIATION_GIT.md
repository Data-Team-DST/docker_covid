# Chantier — Réconciliation `chore/claude-code-setup` ↔ `main`/`dev` — ✅ CLOS (2026-08-27)

**Résolu** : PR #27 (`chore/claude-code-setup` → `dev`) puis PR #28 (`dev` → `main`), toutes
deux mergées le 2026-08-27, CI complète verte sur les deux. Décisions de résolution des
conflits listés ci-dessous (renommage modèles, `params.yaml`, `dvc.lock`, module
`trainer/src/ds_covid`) appliquées comme décrit. Deux bugs CI préexistants (indépendants de
cette réconciliation) trouvés et corrigés au passage : smoke-test backend crashant faute
d'`API_KEY` en prod, lockfile `backend/requirements-dev.txt` cassé par un bloc dupliqué. US-18
(non traité ici, hors scope) : voir `CHANTIER_US18.md`.

---

Ouvert le 2026-08-27, suite à une session de pipeline DVC GPU complet (classification +
segmentation) sur `chore/claude-code-setup`. **Contrairement à `CHANTIER_INFRA_SERVICES.md`,
ce chantier n'est pas à reporter après la soutenance** — c'est une divergence git qui
s'aggrave à chaque nouveau commit de part et d'autre, et qui bloque déjà un `git push` propre
depuis hier soir. À traiter en premier, dès qu'il y a un créneau avec la tête reposée (pas à
2h du matin après une session GPU).

## Constat de fond

La PR #26 (`chore/claude-code-setup`) a été **mergée dans `main` à un moment donné**
(`4612081 Merge pull request #26 from Data-Team-DST/chore/claude-code-setup`). Depuis, les
deux lignées ont continué à évoluer **indépendamment** :

- `main` : ~30 commits d'avance sur notre point de départ commun, en grande partie la suite
  du travail de Rafael sur `raf5` (segmentation-service, fixes GPU/MLflow/DagsHub, renommage
  des modèles) + un fix lint/CI récent (`dc42ba0`, `bioinfodl`).
- `chore/claude-code-setup` (branche locale actuelle) : ~30 commits d'avance de notre côté
  (réorg structurelle `trainer/`, récupération de la suite complète de `raf5` en parallèle,
  US-20 monitoring Evidently, et ce soir un pipeline DVC GPU complet).
- `dev` : a en plus `e178411 merge us18 to dev`, pas encore intégrée nulle part dans `main`
  ni dans notre branche.

**Aucune des trois lignées n'est un sous-ensemble d'une autre.** Un simple `git push` ou un
rebase naïf perdrait du travail réel des deux côtés.

## Ce qui est en conflit réel (pas juste "peut-être des conflits")

### 1. Nommage des fichiers modèles

- `main` : `data/models/classification.keras` / `data/models/segmentation.keras` — renommé
  par Rafael dans `72c3b25 fix(models): unifier les noms de fichiers .keras entre DVC et
  les consommateurs`, touche 14 fichiers (`dvc.yaml`, les 4 scripts `trainer/scripts/*.py`,
  `backend/app/config.py`, `segmentation-service/src/segmentation_service/{config,model}.py`,
  `infrastructure/docker-compose.yml`, `infrastructure/scripts/setup.sh`,
  `.github/workflows/cicd.yml`, `README.md`, `docs/us-verification.md`, `.env.example`).
- Notre branche : `data/models/covid_model.keras` / `data/models/lung_unet.keras` — jamais
  renommé, tous les fichiers ci-dessus divergent en conséquence.
- **Piste** : adopter le renommage de Rafael (plus lisible, déjà propagé partout côté main),
  reporter nos propres changements (fix batch_size segmentation, structure `trainer/`) par-dessus.

### 2. `params.yaml` — `max_samples_per_class`

- `main` : déjà repassé à `null` (dataset complet) — `1d1b84a chore(params): repasser
  max_samples_per_class à null (dataset complet)`.
- Notre branche : `1500` (valeur intermédiaire, validée ce soir avec un run GPU complet
  capé).
- **Non vérifié avant de trancher** : est-ce que le `dvc.lock` de main (`b6bd476 chore:
  mettre à jour dvc.lock après le pipeline GPU complet`) correspond à un run **réellement
  poussé sur DagsHub** (pas juste committé — même piège que celui rencontré hier avec le
  `covid_model.keras` de `raf5`, jamais confirmé pushé) ? À demander directement à Rafael
  avant de décider si son run est utilisable tel quel ou s'il faut en relancer un.

### 3. Fix OOM segmentation (`batch_size`)

- Identique des deux côtés (`c563b8b` sur main, redécouvert indépendamment ce soir) — pas de
  conflit réel, juste un doublon. Sans risque à fusionner.

### 4. `dvc.lock` — deux pipelines complets concurrents

- Notre branche a un `dvc.lock` à 7 stages, généré et poussé sur DagsHub ce soir (commit
  `d962169`), sur dataset capé à 1500/classe, noms `covid_model.keras`/`lung_unet.keras`.
- `main` a potentiellement un autre `dvc.lock` complet (`b6bd476`), sur dataset complet (si
  confirmé pushé), noms `classification.keras`/`segmentation.keras`.
- Il ne peut y en avoir qu'un des deux qui "gagne" — pas une fusion automatique possible sur
  ce fichier (généré, pas éditable à la main).

## Travail à ne PAS perdre en réconciliant (unique à notre branche, absent de `main`/`dev`)

Vérifié par `git diff --stat origin/main...HEAD` et recherche `evidently`/`monitoring`/`US-20`
sur `main`/`dev` (aucune occurrence) :

- `trainer/scripts/drift_report.py` (US-20, rapport de dérive Evidently) — **106 lignes,
  n'existe nulle part ailleurs**.
- `segmentation-service/tests/{test_config,test_health,test_model}.py` — 3 fichiers de tests.
- `trainer/requirements.txt` — lockfile `pip-compile --generate-hashes` (4788 lignes, validé
  en conteneur Linux propre, cf. `TODO.md` #2).
- Réorganisation structurelle `trainer/` colocalisé (Dockerfile, scripts, `src/ds_covid/`) —
  documentée comme l'architecture actuelle dans `CLAUDE.md`, à confirmer que `main` l'a aussi
  ou si elle est encore à `infrastructure/docker/trainer/` côté main.
- `TODO.md` consolidé (journal de bord détaillé de toute la session de récupération raf5).

## Stratégie recommandée (à valider en équipe avant exécution)

**Un seul merge, pas un rebase** — rebaser 30 commits divergés sur 30 commits divergés qui
touchent les mêmes fichiers (renommage modèles notamment) reviendrait à résoudre le même
conflit commit par commit. Un merge unique concentre la résolution en un seul point.

1. Confirmer avec Rafael si le `dvc.lock` de `main` (`b6bd476`) est un run complet
   effectivement poussé sur DagsHub, ou juste committé.
2. `git merge origin/main` dans notre branche (ou l'inverse, à discuter) — résoudre les
   conflits ci-dessus : adopter le nommage `classification.keras`/`segmentation.keras` de
   Rafael, adopter `max_samples_per_class: null` si le run de main est valide, garder notre
   fix batch_size (identique), choisir quel `dvc.lock` fait foi (probablement celui du run
   sur dataset complet si confirmé valide, sinon relancer un `dvc repro` propre après le
   merge du code).
3. Merger `origin/dev` par-dessus (récupère US-18).
4. Vérifier US-18 avec `dashboard` (demande explicite de Steven).
5. Build complet + tests des services touchés par le renommage (`backend`,
   `segmentation-service`, `trainer`).
6. PR de la branche réconciliée vers `dev`, puis `dev` → `main`.

## Pas fait dans ce chantier (volontairement)

Aucune modification appliquée — recherche/constat uniquement. Rien mergé, rien renommé,
rien pushé.
