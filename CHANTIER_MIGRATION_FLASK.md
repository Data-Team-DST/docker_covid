# Chantier — Migration frontend Streamlit → Flask

> Document de cadrage, pas un plan d'exécution. Destiné à être repris par une autre conversation
> Claude Code pour être affiné puis exécuté. Rien n'a été commencé côté code.

## Pourquoi ce chantier

Le frontend (`frontend/`) est un multi-page Streamlit. Son architecture impose un pattern
structurel : chaque page (`frontend/page/NN_nom/`) fait un `sys.path.insert(0, ...)` avant
d'importer ses modules frères, parce que Streamlit charge chaque page comme un script
autonome, sans notion de package Python standard. Conséquence documentée dans
`.claude/rules/python/sonarqube.md` (section *"Imports après sys.path.insert() — exemption
documentée"*) : ~20 disables `invalid-name`/`wrong-import-position`/`import-error`/
`non-ascii-file-name` sont structurellement nécessaires et ne peuvent pas être supprimés sans
casser l'ordre d'affichage des pages ou l'import des modules.

Le projet a déjà une app Flask fonctionnelle dans `dashboard/` (backlog agile + data explorer,
US-17) — remplacer Streamlit par Flask pour le frontend principal éliminerait cette classe
entière de code smell structurel et unifierait la stack web du projet sur un seul framework.

## Contrainte non négociable : la soutenance

**Soutenance le 2026-09-04.** Le frontend sert de support de présentation (US à définir/
retrouver dans `dashboard/backlog.yaml` — vérifier son intitulé exact et son statut avant de
commencer). Ce chantier ne doit **en aucun cas** être exécuté, ni même commencé côté code, avant
d'avoir une confirmation explicite que :
- soit la soutenance est passée,
- soit une US dédiée à la présentation (contenu, déroulé, support) a été identifiée et que le
  chantier ne la met pas en péril (ex. migration faite bien en amont avec marge de test, ou
  un mode de secours Streamlit conservé en parallèle jusqu'à validation complète de la version
  Flask).

Toute conversation reprenant ce document doit **commencer par relire `CLAUDE.md` § Calendrier**
(à jour au moment de la reprise, pas figé à la date de rédaction de ce fichier) et confirmer
avec l'utilisateur que la fenêtre de temps disponible est compatible avec l'ampleur du chantier
avant d'écrire la moindre ligne de code.

## Périmètre actuel à cartographier (état au 2026-08-24)

- `frontend/streamlit_app.py` — point d'entrée, thème, navigation (`_nav.py`, `_styles.py`),
  chargement dynamique des pages via `frontend/page/_loader.py`.
- 7 pages dans `frontend/page/` : `01_accueil`, `02_donnees`, `03_preprocessing`,
  `04_Machine_learning_et_optimisation`, `05_Deep_learning_et_Interprétabilité` (fichier seul,
  pas de package), `06_cicd`, `07_conclusion_critique_perspective`.
- Chaque page-package (`NN_nom/`) a un `__init__.py` (point d'entrée `run()`) + des modules
  internes (`_sections.py`, `_ui.py`, `_data_utils.py`, etc.).
- Widgets Streamlit utilisés à inventorier précisément avant de chiffrer le chantier :
  `st.selectbox`, `st.columns`, `st.container`, `st.cache_data`/`st.cache_resource`,
  `st.session_state`, `st.image`, composants tiers (`streamlit_extras.colored_header`).
- `06_cicd/` contient une UI interactive de construction de pipeline sklearn
  (`_pipeline_create.py`, `_pipeline_load.py`, etc.) — **actuellement cassée** (voir
  `CHANTIER_BUGS_06_CICD.md` si ce fichier existe encore, sinon voir l'historique de
  conversation du 2026-08-24) : import mort vers des classes supprimées. À trancher avant la
  migration : reproduire cette fonctionnalité en Flask, ou la couper définitivement (elle n'a
  peut-être plus de raison d'être si elle est déjà non fonctionnelle).

## Questions à trancher avant de chiffrer

1. **Portée** : migration intégrale des 7 pages, ou uniquement celles qui seront montrées à la
   soutenance ?
2. **Approche technique Flask** : Jinja2 + JS minimal (cohérent avec `dashboard/`), ou
   Flask + HTMX pour garder de l'interactivité sans reconstruire un SPA ? Pas de framework JS
   lourd (React/Vue) sans en discuter — le projet est mono-stack Python.
3. **État/cache** : Streamlit gère `st.session_state`/`st.cache_*` nativement. Flask n'a rien
   d'équivalent out-of-the-box — prévoir explicitement la stratégie (session Flask, cache
   applicatif, recalcul à chaque requête).
4. **Que fait-on de `06_cicd/` (pipeline builder cassé)** — cf. ci-dessus.
5. **CI/CD** : `cicd.yml` build une image `covid-xray-streamlit` — un nouveau Dockerfile Flask
   et une nouvelle image seraient nécessaires, `infrastructure/docker-compose.yml` et
   `infrastructure/kubernetes/streamlit.yaml` à adapter.
6. **Coexistence pendant la migration** : migrer page par page avec les deux apps en parallèle
   le temps de valider, ou big-bang ? Recommandation par défaut : page par page, avec le
   Streamlit existant qui continue de tourner jusqu'à ce que l'équivalent Flask soit validé.

## Ce que ce document ne fait pas

- Il ne chiffre pas le chantier en heures/jours.
- Il ne choisit pas l'approche technique Flask (Jinja2 vs HTMX vs autre) — c'est à trancher
  avec Steven au moment de la reprise.
- Il ne touche à aucun fichier de code.

## Prochaine étape recommandée pour qui reprend ce chantier

1. Relire `CLAUDE.md` § Calendrier + confirmer avec Steven que la fenêtre de temps est sûre.
2. Auditer précisément les 7 pages (widgets, état, dépendances) — produire un inventaire avant
   de proposer une architecture Flask cible.
3. Trancher les questions de la section précédente avec Steven avant d'écrire du code.
4. Proposer un plan de migration page par page avec un ordre de priorité (pages critiques pour
   la soutenance en dernier, une fois la mécanique validée sur des pages moins sensibles).
