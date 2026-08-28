# Chantier — Scinder `dashboard` en `dashboard` (backlog + data explorer) + `demonstration/` (démo produit)

Ouvert le 2026-08-28, suite au chantier `CHANTIER_INFRA_SERVICES.md` (clos, supprimé le même
jour — § 2 y notait déjà ce mélange de responsabilités comme un sujet reporté). **À traiter
avant la soutenance du 04/09/2026, pas après** : Steven a précisé qu'il n'y a pas de créneau
de reprise post-soutenance (voir mémoire projet), contrairement à l'hypothèse initiale du
chantier précédent.

**Exécution prévue dans une autre conversation** — ce fichier documente le plan validé, cette
session-ci servira à vérifier le livrable une fois fait.

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

## Pas fait dans ce chantier (à date du 2026-08-28)

Aucune modification appliquée — ce fichier documente le plan validé par Steven en session,
avant exécution dans une autre conversation. Une fois fait : mettre à jour `CLAUDE.md`
(architecture réelle, section `dashboard/` + nouveau `demonstration/`), `TODO.md`, et
supprimer ou clore ce fichier selon le même principe que les chantiers précédents.
