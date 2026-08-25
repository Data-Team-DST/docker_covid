<!-- Généré : 2026-08-24 | Fichiers scannés : 28 | ~300 tokens -->

# Frontend — Streamlit :8501

Multi-page app, chaque page top-level (`0N_nom.py`) délègue à un sous-package `0N_nom/`
(`__init__.py` = orchestration, `_*.py` = sections privées). Pattern répété sur les 6 pages
avec sous-package — cohérent avec le reste du repo (imports après `sys.path.insert`, d'où les
nombreux `# noqa: E402` documentés dans `docs/friday-audits/`).

## Page tree

```
streamlit_app.py            entrée — thème sombre, nav dynamique (_nav.py, _styles.py, page/_loader.py)

page/01_accueil.py          → page/01_accueil/{__init__, _context, _objectives}.py
page/02_donnees.py          → page/02_donnees/{__init__, _config, _data_utils, _ui, _visualizations}.py
page/03_preprocessing.py    → page/03_preprocessing/{__init__, _sections}.py
page/04_Machine_learning_et_optimisation.py
                             → page/04_.../{__init__, _confusion_matrices, _sections}.py
page/05_Deep_learning_et_Interprétabilité.py   (page simple, pas de sous-package)
page/06_cicd/                → page/06_cicd/{__init__, _sections}.py
page/07_conclusion_critique_perspective.py     (page simple)
```

## Notes structurelles

- `page/06_cicd/` ne contient plus que la présentation pédagogique du pipeline CI/CD
  (`_sections.py`) — le pipeline builder sklearn interactif (`_pipeline_*.py`, appelait
  `src.features.St_Pipeline.Transformateurs`, cassé depuis la migration microservices) a été
  retiré le 2026-08-24, aucune US ne le référençant.
- Pas de tests dédiés au frontend à ce jour (`test_fe` en CI tourne en `continue-on-error: true`
  tant qu'aucun `test_*.py` n'existe sous `frontend/`).
