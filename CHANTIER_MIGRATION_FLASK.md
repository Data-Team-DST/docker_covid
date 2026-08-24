# Chantier — Support de soutenance : prédicteur live + pages preuve par sprint

> Document de cadrage, pas un plan d'exécution. Rien n'a été commencé côté code.

## Historique

Ouvert le 2026-08-24 sous le titre "Migration frontend Streamlit → Flask". Discussion la
même journée avec Steven : le cadrage initial (porter les 7 pages `frontend/` à l'identique
vers Flask) est **entièrement abandonné** au profit de ce qui suit, après audit du contenu
réel des pages et clarification de l'objectif (support de soutenance MLOps, pas nettoyage de
dette).

## Décisions actées (2026-08-24)

**Les 7 pages `frontend/` (`01_accueil` → `07_conclusion`) sont l'héritage du projet Data
Science de l'année précédente (DS_COVID), pas du travail MLOps.** Audit page par page
(contenu réel lu, pas supposé) :

| Page | Contenu réel |
|---|---|
| 01_accueil | Contexte projet + objectifs SMART, noms de l'équipe |
| 02_donnees | Présentation dataset Kaggle, déséquilibre de classes, aperçus d'images |
| 03_preprocessing | Masking, déséquilibre, augmentation |
| 04_ML et optimisation | Liste de modèles, matrices de confusion, grid search |
| 05_Deep learning et Interprétabilité | SHAP/LIME sur le CNN |
| 06_cicd | Pipeline builder cassé (→ suppression actée, voir `CHANTIER_ST_PIPELINE.md`) + explication pédagogique générique du CI/CD |
| 07_conclusion | "POC analytique", limites méthodologiques, biais |

Zéro contenu lié à l'industrialisation MLOps (Phase 1-4 : API, Docker, CI/CD, K8s, DVC,
MLflow, monitoring) — c'est exactement ce qui est noté à la soutenance. Conséquence :

- **Aucune des 7 pages n'est migrée individuellement.** Au mieux, une seule page condensée
  "contexte / origine DS" (reprenant `01_accueil` + un résultat baseline de `04`/`05`) pour
  situer d'où le projet part. Sinon : on ne les touche pas, on ne les maintient pas.
- `06_cicd` : partie pédagogique générique abandonnée aussi — redondante face à la vraie
  preuve de sprint S3 (voir plus bas).
- Le "pipeline builder" cassé de `06_cicd` : suppression définitive, décision déjà actée
  dans `CHANTIER_ST_PIPELINE.md` (option C).

**Le prédicteur live (upload radio → prédiction) n'existe nulle part aujourd'hui** — vérifié
par grep (`file_uploader`, `predict`) sur tout `frontend/` : zéro résultat. Ce n'est donc pas
une migration, c'est une construction neuve. Jugé utile : c'est la preuve la plus parlante
pour un jury MLOps (upload → classe/confiance via l'API réellement déployée), coût de
construction faible, endpoint backend `/api/v1/predict` déjà testé à 95% de coverage.
→ À construire, directement en Flask.

**Les pages "preuve de travail par sprint" (S1→S4+HS)** sont construites en extension de
`dashboard/` — déjà Flask + Jinja2, déjà structuré par sprint via `backlog.yaml`
(`dashboard/templates/index.html` affiche déjà les KPI par sprint), déjà zéro dette de
déploiement (absent de `docker-compose.yml`, des manifests K8s et de `cicd.yml` — donc zéro
risque sur la stack qui tourne pour la démo). Pour chaque story du backlog, ajouter la preuve
(capture d'écran et/ou lien repo — commit/fichier/PR) à côté de la description déjà présente.

## Nouveau périmètre (remplace intégralement l'ancien)

1. **Prédicteur live neuf**, Flask : formulaire upload + appel `POST /api/v1/predict` +
   affichage classe/confiance/scores.
2. **Pages détail par sprint** dans `dashboard/` (S1, S2, S3, S4, HS) : preuve (capture/lien)
   par story, en s'appuyant sur `backlog.yaml` existant.
3. Optionnel : une page condensée "contexte DS" côté `frontend/` — sinon rien.

## Ce que ce document ne fait pas

- Il ne chiffre pas en heures/jours.
- Il ne code rien — décisions actées, exécution à faire.
- Il ne choisit pas l'ordre d'exécution entre le prédicteur et les pages sprint — à trancher
  au moment de la reprise.

## Prochaine étape

Démarrer sur le prédicteur live et/ou les pages sprint `dashboard/`, en parallèle de US-22
(documentation finale) menée par Steven et des items Phase 4 (Prometheus/Grafana/Evidently/
retrain) menés par le reste de l'équipe.
