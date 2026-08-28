# Chantier — Scinder `dashboard` en `dashboard` (backlog + data explorer) + `demonstration/` (démo produit)

Ouvert le 2026-08-28, suite au chantier `CHANTIER_INFRA_SERVICES.md` (clos, supprimé le même
jour — § 2 y notait déjà ce mélange de responsabilités comme un sujet reporté). **À traiter
avant la soutenance du 04/09/2026, pas après** : Steven a précisé qu'il n'y a pas de créneau
de reprise post-soutenance (voir mémoire projet), contrairement à l'hypothèse initiale du
chantier précédent.

**Phase 1 exécutée et vérifiée le 2026-08-28** (cette même session, sur demande explicite de
Steven — "go !"). **Phase 2 (nav fluide htmx) reste à faire.**

---

## Constat

`dashboard/app.py` (Flask, fichier unique, 466 lignes, 17 routes) porte aujourd'hui deux
responsabilités distinctes, aggravées par la migration du contenu `frontend/` faite au point 15 :

- **Outil interne** : backlog agile (sprints, résolution de commits, `state.json`/`backlog.yaml`)
- **Façade démo produit** : contexte, prédicteur live, préprocessing, modèles, conclusion, data explorer

Screenshot de la nav actuelle (fourni par Steven en session) : `Contexte DS · Prédicteur ·
Préprocessing · Modèles · Conclusion · Data Explorer` — 6 onglets produit en plus du backlog,
tous dans le même service Flask.

**Second problème signalé, indépendant du split** : naviguer entre les onglets actuels de
`dashboard` demande des allers-retours pénibles (chaque clic recharge toute la page — classique
multi-page Flask, pas un bug, mais nuit à la fluidité). Confirmé par Steven comme **déjà
présent aujourd'hui**, pas seulement anticipé après le split.

## Décision actée

**Option B** (des 3 posées dans l'ancien `CHANTIER_INFRA_SERVICES.md` § 2) : garder `dashboard`
tel quel pour le backlog + data explorer, créer un nouveau service `demonstration/` dédié pour
le contenu de présentation. Pas d'Option A (scinder `dashboard` en deux moitiés différemment),
pas d'Option C (rester en l'état).

### Répartition exacte des routes (`dashboard/app.py` actuel)

**Reste dans `dashboard/`** (backlog + data explorer) :
| Route | Rôle |
|---|---|
| `/` | Backlog board (`index.html`) |
| `/sprint/<sprint_id>` | Détail sprint (`sprint_detail.html`) |
| `/api/toggle` | Toggle statut item backlog |
| `/api/sprint-status` | Update statut sprint |
| `/data` | Data Explorer (`data_explorer.html`) |
| `/api/data-stats` | Proxy → data-service `/v1/data/stats` |
| `/api/dvc/<action>` | Proxy → dvc-service `/v1/dvc/*` |
| `/api/ds/stats`, `/search`, `/image`, `/sample`, `/metrics` | Proxies → data-service `/v1/data/*` |

**Part dans `demonstration/`** (nouveau service) :
| Route | Rôle | Template |
|---|---|---|
| `/contexte` | Contexte DS | `contexte.html` |
| `/conclusion` | Conclusion critique/éthique | `conclusion.html` |
| `/preprocessing` | Préprocessing (env, masking, augmentation) | `preprocessing.html` |
| `/predict` | Prédicteur live → backend `/api/v1/predict` | `predict.html` |
| `/modeles` | Statut modèles (MLflow Registry, provenance live) | `model_status.html` |

Images statiques associées à déplacer avec leurs templates (`dashboard/static/img/*` — trier
lesquelles sont utilisées par `contexte`/`preprocessing`/`modeles` vs par `data_explorer`
avant de couper, ne pas dupliquer ni deviner).

## Plan d'exécution — en 2 phases séparées, pas un seul gros commit

**Rationale** : ne pas mélanger un changement structurel (nouveau service) avec un changement
de comportement (navigation) dans le même chantier — plus facile à vérifier/bisecter si
quelque chose casse à quelques jours de la démo.

### Phase 1 — Split mécanique (routes déplacées à l'identique, zéro changement de comportement)

1. Nouveau service `demonstration/` : même pattern simple que `dashboard` (Flask, fichier
   unique, pas de couche router/service séparée — cohérent avec la convention actuelle du
   projet pour ce type de service).
2. Déplacer les 5 routes + templates + assets listés ci-dessus.
3. Choisir un port libre (`dashboard` = 5050, non catalogué dans
   `infrastructure/docker-compose.yml` — lancé à part comme `dashboard` aujourd'hui, ou
   ajouté au compose : à trancher pendant l'exécution).
4. Mettre à jour `Makefile` (nouvelle section `demonstration-*`, mirroir de la section
   `dashboard` existante), `README.md`, tout lien croisé entre les deux services (`predict.html`
   appelle le backend directement — pas de dépendance à `dashboard` lui-même à conserver).
5. **Vérifier en conditions réelles** : les deux services démarrent, chaque page rend
   exactement comme avant (contenu, images, styles), `/predict` fonctionne toujours contre le
   backend réel, `/data` (resté dans `dashboard`) inchangé.

### Phase 2 — Fluidité de navigation (une fois Phase 1 validée stable)

Fix choisi : **htmx** (bandeau de nav fixe par service, seul le contenu central se recharge en
AJAX au clic — pas de framework JS lourd, pas de réécriture du templating Jinja existant,
cohérent avec la stack actuelle). Appliqué **à l'intérieur de chaque service** (nav fluide au
sein de `dashboard`, nav fluide au sein de `demonstration/`) — pas de pont inter-services
prévu pour l'instant (pas demandé, ajouterait un reverse-proxy unifiant les deux origines,
sujet séparé si besoin plus tard).

## État — Phase 1 faite le 2026-08-28

- Nouveau service `demonstration/` créé (`app.py`, `requirements.in`/`requirements.txt`
  hash-locké généré en conteneur Linux `python:3.11-slim`, `templates/`, `static/`) — port
  5051, choisi libre (5050 dashboard, 5051 suite logique, non catalogué ailleurs).
- 5 routes + templates + les 20 images associées (`contexte`, `preprocessing`) déplacées
  depuis `dashboard/` vers `demonstration/` (suppression des originaux confirmée par Steven,
  copies vérifiées identiques par `diff` avant suppression). `style.css` dupliqué (5 lignes,
  utilisé des deux côtés) ; `static/img/anomalies/*` (8 fichiers, `data_explorer.html`) et
  `style.css` restent dans `dashboard/`.
- Liens croisés inter-services : `dashboard/app.py` et `demonstration/app.py` injectent
  respectivement `demonstration_url`/`dashboard_url` via `@app.context_processor`
  (`DEMONSTRATION_URL`/`DASHBOARD_URL`, env vars, défaut `localhost:5051`/`:5050`) — tous les
  `href="/xxx"` qui traversaient la frontière de service mis à jour dans les templates des
  deux services ; les liens same-service restent relatifs.
- `API_KEY` retiré de `dashboard/app.py` (mort après le départ de `/predict`, seul
  consommateur).
- `Makefile` : cibles `setup-demonstration`/`demonstration` ajoutées (miroir de
  `setup-dashboard`/`dashboard`, sans MinIO/data-service/dvc-service — `demonstration/` ne
  dépend que du backend). `.PHONY` mis à jour.
- `README.md` (arborescence + tableau des services), `CLAUDE.md` (architecture réelle),
  `TODO.md` (point #15 clos avec résumé) mis à jour.
- **Vérifié en bac à sable réel** (CLAUDE.md règle #9) : copie ciblée `dashboard/` +
  `demonstration/` (sans `.venv`) dans un dossier scratch, conteneur `python:3.11-slim`,
  deps installées `--require-hashes`, les deux Flask lancés en même temps avec les bonnes
  env vars croisées. Résultat : 7/7 pages 200, liens croisés résolus (`http://localhost:5051/...`
  et `http://localhost:5050/...` bien injectés, zéro `{{`/`}}` non résolu), assets statiques
  (CSS + images des deux services) accessibles, `POST /predict` retombe correctement sur
  "Backend inaccessible" (pas de backend dans ce bac à sable — chemin d'erreur testé, pas
  l'inférence réelle). `ruff check --line-length 88` propre sur les deux `app.py`.
- Pas exécuté dans ce bac à sable (hors périmètre de la vérification mécanique) :
  `make lint-full`/`make test` sur l'ensemble du repo, et un test `/predict` avec un vrai
  backend + modèle chargé.

## Reste à faire

- **Phase 2 (nav fluide htmx)** — pas commencée. À reprendre dans une session dédiée une
  fois Phase 1 confirmée stable par Steven.
- Fermer ce fichier (suppression, résumé dans `TODO.md`) une fois Phase 2 faite — pas avant,
  suivant le même principe que les chantiers précédents.
