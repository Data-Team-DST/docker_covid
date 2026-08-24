# SonarQube — Règles gravées dans le marbre

Ces règles sont issues d'une séance de correction post-scan (mai 2026, 37 code smells + 2 security hotspots).
Les respecter **avant** chaque commit pour ne pas se faire retaper par SonarQube.

## Complexité cognitive ≤ 15 (python:S3776)

Chaque fonction doit avoir une complexité cognitive ≤ 15.
Si `if/for/while` imbriqués font monter le compteur, **extraire des fonctions helpers** :

```python
# ❌ CC = 78 — refus SonarQube
def _extract_xlsx(path):
    for ws in wb.worksheets:
        for r in range(...):
            for c in range(...):
                if condition1:
                    if condition2:
                        ...

# ✅ CC < 15 — chaque helper a sa propre responsabilité
def _xlsx_cell_str(grid, r, c): ...
def _xlsx_build_headers(grid, nb_rows, max_col): ...
def _xlsx_sheet_with_headers(grid, ...): ...
def _xlsx_sheet_flat(grid, ...): ...
def _xlsx_process_sheet(ws, grid): ...
def _extract_xlsx(path):
    for ws in wb.worksheets:
        grid = _build_grid(ws)
        parts, count = _xlsx_process_sheet(ws, grid)
```

## Docstrings obligatoires (python:S1192 + python:S5720)

**Toutes** les classes et fonctions publiques ou protégées doivent avoir une docstring.
Une ligne suffit — mais elle est obligatoire :

```python
# ❌
class ExtractionResult:
    ...

def _safe_path(base_dir, filename):
    ...

# ✅
class ExtractionResult:
    """Résultat normalisé d'une extraction de texte."""
    ...

def _safe_path(base_dir: Path, filename: str) -> Path:
    """Résout filename sous base_dir et rejette tout path traversal."""
    ...
```

Cas particuliers SonarQube :
- Modèles Pydantic (`BaseModel`) : docstring sur la classe
- Fonctions imbriquées (`def _progress()` dans `_do_convert`) : docstring requise
- Inner classes : docstring requise

## Littéraux dupliqués → constantes (python:S1192)

Si une chaîne apparaît ≥ 3 fois dans un fichier, l'extraire en constante module-level :

```python
# ❌
if path.suffix.lower() == ".docx":
    ...
if filename.endswith(".docx"):
    ...
return {"type": ".docx"}

# ✅
EXT_DOCX = ".docx"

if path.suffix.lower() == EXT_DOCX:
    ...
```

Seuil SonarQube : 3 occurrences identiques déclenchent une violation.

## Profondeur d'imbrication ≤ 4 (python:S134)

Maximum 4 niveaux d'indentation (fonction → if → for → if). Au-delà, extraire :

```python
# ❌ — 5 niveaux
def process():
    if condition1:          # 1
        for item in items:  # 2
            if condition2:  # 3
                for x in item:  # 4
                    if x:       # 5 ← violation
                        ...

# ✅ — extraire le corps interne
def _process_item(item):
    for x in item:
        if x:
            ...

def process():
    if condition1:
        for item in items:
            if condition2:
                _process_item(item)
```

## Security Hotspots : faux positifs XML namespace (python:S5332)

SonarQube signale les URLs `http://schemas.openxmlformats.org/...` comme connexions HTTP non sécurisées.
Ce sont des **identifiants XML namespace**, pas des connexions réseau. Seule correction autorisée : `# NOSONAR` sur la ligne.

```python
# ✅ — seule solution valide : NOSONAR documenté
NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",  # NOSONAR
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",  # NOSONAR
}
```

### ⛔ INTERDIT — zéro contournement silencieux

**Ne jamais modifier le littéral pour tromper le scanner.**  
Remplacer `http://` par `https://` dans un namespace XML *casse le standard OOXML* — python-docx et openpyxl ne reconnaîtront plus le namespace et lèveront des erreurs silencieuses à l'exécution. C'est une fausse correction qui masque le problème sans le résoudre.

> **Règle** : si une correction semble consister à "ajouter un s à http" ou à renommer/préfixer un littéral pour faire disparaître une alerte — **STOP, ne pas appliquer, questionner Steven en premier.**  
> On cherche toujours la vraie solution ensemble.

En résumé :
- `# NOSONAR` avec justification → ✅ (faux positif documenté, assumé)
- Modifier le littéral pour contourner → ❌ (correction cosmétique qui casse la fonctionnalité)

## SSL/TLS : jamais `verify=False` (python:S4830)

Utiliser la variable d'environnement pour gérer les CA d'entreprise :

```python
# ❌
requests.get(url, verify=False)

# ✅ — laisse l'env décider (CA bundle entreprise ou True par défaut)
requests.get(url, verify=os.environ.get("REQUESTS_CA_BUNDLE", True))
```

## CORS : `allow_credentials` conditionnel (web:S5122)

`allow_origins=["*"]` + `allow_credentials=True` est invalide per RFC 6454.
Starlette remplace silencieusement `*` par l'origin de la requête — toutes les origines acceptées avec credentials.

```python
# ❌
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True)

# ✅
_CORS_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=_CORS_ORIGINS != ["*"],  # credentials seulement si origins explicites
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Exceptions génériques silencées (python:S110)

```python
# ❌ — bare except silencieux, SonarQube se plaint
try:
    ...
except Exception:
    pass

# ✅ — annoter avec noqa pour justifier le silence délibéré
try:
    ...
except Exception:  # noqa: BLE001
    pass
```

## Imports après `sys.path.insert()` — exemption documentée (`frontend/page/*.py`)

Décision actée le 2026-08-24 (audit `/friday`, 71 disables lint recensés dans `frontend/`,
majoritairement dans `frontend/page/`). Les pages Streamlit multi-pages de ce projet font
`sys.path.insert(0, ...)` avant d'importer des modules frères (`utils`, modules partagés
hors package installable) — pattern structurellement nécessaire à Streamlit, qui charge
chaque page comme script autonome sans notion de package. Ça déclenche
`E402`/`PLC0415`/`wrong-import-position`/`import-error` sur les imports qui suivent.

**Exemption de portée limitée** : dans `frontend/page/*.py` uniquement, un
`# noqa: E402` / `# noqa: PLC0415` / `# pylint: disable=wrong-import-position` /
`# pylint: disable=import-error` qui suit un `sys.path.insert(...)` dans le même fichier
est considéré justifié par la présente règle — pas besoin de justification en langage
naturel ligne par ligne pour ce cas précis.

**Ce que cette exemption NE couvre PAS** : les autres disables trouvés dans le même
répertoire lors de cet audit (`broad-exception-caught`, `invalid-name`,
`too-many-locals`, `line-too-long`, `missing-function-docstring`, `unused-import`, `I001`
— environ la moitié des 71 recensés) restent soumis à la règle générale : soit une
justification explicite en commentaire, soit une correction, à traiter séparément (pas
couvert par cette décision, qui porte uniquement sur le pattern d'import Streamlit).

## Checklist avant commit

- [ ] `ruff check` sans erreur + `mypy` sans erreur (voir CLAUDE.md § Qualité)
- [ ] `make test` → coverage ≥ 80% (seuil projet), zéro test cassé
- [ ] Vérifier CC des nouvelles fonctions : pas de boucles imbriquées > 4 niveaux
- [ ] Docstring sur chaque nouvelle classe/fonction
- [ ] Pas de chaîne littérale dupliquée ≥ 3× → constante
- [ ] `verify=False` absent du code
- [ ] `NOSONAR` sur les namespaces XML si nécessaire
