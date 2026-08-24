# Import Cascade — Règles anti-cascade (R1-R11)

Règles de discipline d'import pour éviter les dépendances en cascade dans les microservices.
Applicables à chaque service Python de ce projet.

## R1 — Un seul importeur par module concret

Un module concret (service, repository, handler) ne doit être importé que par **une seule** couche.
Si deux fichiers importent le même module bas niveau, c'est un signal de couplage excessif.

```python
# ❌ Router ET service importent tous les deux data_reader
from data_service.ingestion.extractor import Extractor  # dans router.py
from data_service.ingestion.extractor import Extractor  # dans metadata.py

# ✅ Un seul point d'entrée — router délègue au service, service utilise extractor
```

## R2 — Pas d'import de couche N depuis couche N+2

Un contrôleur/router ne peut pas importer directement depuis la couche infrastructure/repository.
Les accès passent par la couche service/use-case intermédiaire.

```
Router → Service → Repository   ✅
Router → Repository              ❌ (skip de couche)
```

## R3 — Pas d'import circulaire entre modules du même niveau

Deux modules au même niveau hiérarchique (ex. deux services) ne doivent pas s'importer mutuellement.
Si c'est nécessaire, extraire la logique commune dans un module utilitaire partagé.

## R4 — Les utilitaires n'importent pas les services

Les modules `_utils`, `_helpers`, `_config`, `_constants` ne doivent jamais importer depuis les couches
métier (service, repository, domain). Ils fournissent des outils purs sans dépendances vers le haut.

## R5 — Les modèles de domaine sont sans dépendances

Les classes de domaine (entités, value objects, `_model.py`) n'importent que :
- D'autres modèles du même domaine
- Des utilitaires purs (`_utils`, `_config`)
- Jamais depuis les services ou repositories

## R6 — La configuration ne lie pas les services entre eux

Les fichiers `config.py` / `settings.py` définissent des valeurs statiques.
Ils ne doivent pas instancier de services, ni créer de dépendances inter-modules.

## R7 — L'entrée unique par service

Chaque microservice a un seul point d'entrée (`main.py` ou `app.py`).
Ce fichier peut importer du router/app, rien d'autre directement.

## R8 — Pas d'import cross-service par Python

Règle absolue de ce projet : **zéro import Python direct entre microservices**.
Toute communication passe par HTTP `/v1/`. Violer cette règle casse l'isolation des services.

```python
# ❌ INTERDIT — import direct entre services
from data_service.ingestion.extractor import Extractor  # dans backend/

# ✅ Appel HTTP
response = httpx.get("http://localhost:5001/v1/extract/filename.docx")
```

## R9 — Les `__init__.py` restent vides ou minimalistes

Les `__init__.py` ne doivent pas ré-exporter des symboles via `from .module import X`.
Ces ré-exports créent des dépendances implicites difficiles à tracer dans les diagrammes.

## R10 — Les imports relatifs pour les modules du même package

Préférer les imports relatifs (`from .extractor import Extractor`) pour les modules
au sein du même package. Réserver les imports absolus pour les dépendances externes.

## R11 — Documenter les dépendances internes non-évidentes

Si un module doit importer depuis un niveau inhabituel (justifié), ajouter un commentaire
expliquant pourquoi, pour que les futurs mainteneurs ne cassent pas l'invariant :

```python
# Import depuis infrastructure car ce use-case pilote directement le stockage fichier
# (pas de couche repository intermédiaire pour les écritures atomiques)
from data_service.ingestion.metadata import build_metadata
```

## R12 — DI obligatoire quand 2+ modules ont besoin des mêmes primitives (règle edge=1)

**Problème** : si `service_A.py` et `service_B.py` importent tous deux `primitives.py`, ce module aura edge=2 dans le diagramme — violation de R1.

**Lemme des poignées de main** : avec 2 consommateurs indépendants, quel que soit l'endroit où vivent les primitives partagées, le module qui les contient aura toujours edge≥2. "Remonter le module" ne résout pas le problème.

**Solution — Dependency Injection via le router** :
```python
# ❌ — edge=2
service_a.py → import primitives
service_b.py → import primitives

# ✅ — edge=1 : seul router.py importe primitives
router.py → import primitives           # edge=1 ✓
# router passe les fonctions en paramètres aux deux services
service_a(fn=primitives.foo)
service_b(fn=primitives.foo)
```

**Patron concret** : même logique qu'une éventuelle fonction `call_model_fn` injectée
depuis un futur service ML séparé — ce projet n'en a pas encore, mais le principe reste :
- `router.py` est l'unique importeur du module bas niveau
- Il extrait les fonctions nécessaires et les passe en paramètre aux services
- Les services `_service.py` déclarent `fn=None` dans leur signature et n'importent jamais le module bas niveau directement

**Règle** : avant d'écrire `from X import Y` dans un `_service.py` ou `_utils.py` → vérifier si `X` est déjà importé ailleurs. Si oui → ajouter un paramètre, injecter depuis `router.py`.

**Ce que R12 ne concerne PAS** (précision actée 2026-07-11, question posée en
session sur `md_to_docx.py`) : une constante (regex, seuil, template string...)
utilisée **uniquement à l'intérieur du fichier qui la déclare**, sans qu'aucun
autre module ne l'importe, n'a rien à faire dans un `_config.py`. Centraliser
n'a de sens que pour éviter une duplication d'import entre **au moins deux**
fichiers (edge≥2 réel) — pas par principe. Une constante privée
(`_MA_CONSTANTE`) en tête de module reste la bonne pratique tant qu'elle
n'est consommée que localement. Exemples déjà dans ce repo : les regex
`_TABLE_ROW_RE`/`_BULLET_RE`/etc. de `dashboard/src/dashboard/md_to_docx.py`,
`_DOCX_MIME` de `dashboard/src/dashboard/dashboard_service.py`.

## R13 — DI par paramètre simple = piège de patchabilité des tests (routers FastAPI)

**Problème classique** : appliquer R12
en injectant des **paramètres simples** (Path, fonction, str...) dans un
`register_*_routes(router, param1, param2, ...)` capturé par une closure au
moment de la composition des routes (import du module, une seule fois au
démarrage) casse silencieusement les tests qui patchent le nom d'origine
après coup :

```python
# ❌ — piège : param capturé par valeur dans la closure au moment du register_*_routes()
def register_routes(router, embeddings_path: Path) -> None:
    @router.get("/info")
    def get_info():
        return read(embeddings_path)  # valeur figée à l'appel de register_routes()

register_routes(api_router, _EMBEDDINGS_PATH)  # capturé UNE FOIS au démarrage

# Test : silencieusement no-op, get_info() utilise toujours l'ancienne valeur
monkeypatch.setattr("module.router._EMBEDDINGS_PATH", tmp_path)
```

**Solution — regrouper dans une dataclass, lire un attribut à CHAQUE appel** :

```python
# ✅ — la closure capture l'objet cfg (référence stable), pas sa valeur
@dataclass
class RoutesConfig:
    embeddings_path: Path

def register_routes(router, cfg: RoutesConfig) -> None:
    @router.get("/info")
    def get_info():
        return read(cfg.embeddings_path)  # lu dynamiquement à chaque appel

_CFG = RoutesConfig(embeddings_path=_EMBEDDINGS_PATH)
register_routes(api_router, _CFG)

# Test : fonctionne, cfg est le même objet, seul son champ change
monkeypatch.setattr("module.router._CFG.embeddings_path", tmp_path)
# ou pour une fonction : monkeypatch.setattr("module.router._CFG.build_fn", mock)
```

**Règle** : dès qu'un `register_*_routes()` reçoit plus qu'un `router`, regrouper
TOUT (chemins, fonctions injectées, locks, dicts d'état) dans une dataclass
`XxxRoutesConfig` construite une fois par le module appelant, jamais des
paramètres positionnels/nommés simples — même si un seul champ semble avoir
besoin d'être patchable aujourd'hui, un autre le deviendra demain. Nommer
l'instance `_CFG`/`_XXX_CFG` en toutes lettres dans le module qui la construit
pour que les tests sachent quoi patcher.

## Lecture des diagrammes d'import

Dans l'Architecture Lab (dashboard :5050 → 🏗 Architecture) :

- **Flèches** = `A → B` signifie "A importe B"
- **Nœuds avec bordure orange pointillée** = module jamais importé par d'autres (orphelin potentiel)
- **Couleur du nœud** = couche architecturale (vert=entry, orange=routes, bleu=domain, etc.)
- **Doubles flèches** entre deux modules = deux chemins d'import distincts (ex. A importe B via deux `from` différents)

Si le diagramme montre une flèche qui viole R2 ou R8, c'est un code smell à corriger.
