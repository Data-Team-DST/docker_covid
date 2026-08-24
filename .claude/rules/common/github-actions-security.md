# GitHub Actions — règles gravées dans le marbre

Issues d'une correction post-scan SonarQube for IDE (2026-08-17, 5 findings sur `cicd.yml` :
S8264, S8233, S8541 ×5, S8544 ×4, S7637 ×9). Les respecter **avant** chaque commit de workflow
pour ne pas se faire retaper.

## Permissions au niveau job, jamais au niveau workflow (S8264 / S8233)

Un bloc `permissions:` au niveau `workflow` s'applique à **tous** les jobs, même ceux qui n'en
ont pas besoin (ex. un job de lint n'a besoin d'aucune permission d'écriture).

```yaml
# ❌ — accordé à tous les jobs, y compris lint/test qui n'en ont pas besoin
permissions:
  contents: read
  packages: write

# ✅ — deny-all au niveau workflow, chaque job déclare le strict nécessaire
permissions: {}

jobs:
  lint:
    permissions:
      contents: read     # juste ce qu'il faut pour actions/checkout
  build:
    permissions:
      contents: read
      packages: write    # seul job qui push sur ghcr.io
  deploy:
    permissions:
      packages: read     # seul job qui pull, pas de checkout donc pas de contents
```

Un job qui ne fait ni checkout ni appel à un token GitHub (ex. un job `summary` qui écrit
uniquement `$GITHUB_STEP_SUMMARY`) n'a besoin d'aucun bloc `permissions`.

## `pip install` — toujours `--only-binary=":all:"` (S8541)

Sans ce flag, pip peut retomber sur un sdist et exécuter le `setup.py` d'un paquet tiers
pendant le build — exécution de code arbitraire dans le runner CI.

```yaml
# ❌
run: pip install ruff pylint

# ✅ — le flag doit être quoté en YAML (":all:" contient un `: ` qui casse le parsing sinon)
run: pip install --only-binary=":all:" ruff==0.16.0 pylint==3.3.9
```

## Versions verrouillées, jamais flottantes (S8544)

Un `pip install paquet` sans version tire toujours la dernière release au moment du run —
non reproductible, et une release compromise entre deux runs passe inaperçue.

```yaml
# ❌
run: pip install ruff pylint mypy bandit

# ✅ — version exacte, vérifiée résolvable via `pip index versions <paquet>` avant de committer
run: pip install --only-binary=":all:" ruff==0.16.0 pylint==3.3.9 mypy==1.18.2 bandit==1.9.4
```

**Avant de choisir une version** : vérifier qu'elle existe réellement sur PyPI
(`pip index versions <paquet>`) — un pin sur une version inexistante casse le pipeline plus
sûrement que le finding qu'on corrige. Rester dans la même ligne majeure que ce qui est déjà
utilisé ailleurs dans le repo (`dev-requirements.txt`, etc.) sauf si une montée de version est
explicitly demandée.

**Épingler en `==` ne suffit pas quand l'install passe par `-r fichier.txt`** (contrairement à un
`pip install paquet==1.0.0` en ligne de commande, que SonarQube accepte tel quel). Pour toute
ligne `pip install -r fichier.txt`, la règle veut `--require-hashes` — un `==` seul dans le
fichier ne l'éteint pas :

```yaml
# ❌ — le fichier référencé a beau être en == exact, le finding reste
run: pip install -r requirements.txt

# ✅
run: pip install --require-hashes -r requirements.txt
```

`--require-hashes` a une contrainte stricte : **toute** dépendance résolue par pip — y compris
les transitives, y compris tout paquet passé en argument brut sur la même ligne de commande
(`pip install --require-hashes -r a.txt paquet==1.0` échoue, `paquet` n'a pas de hash possible
en CLI) — doit avoir un hash. Ça implique deux choses :

1. Ne jamais mélanger `-r fichier.txt` et des paquets nus sur la même commande — tout doit être
   dans le fichier.
2. Le fichier référencé doit lister le graphe **complet**, transitives comprises, chacune avec
   son hash — pas juste les paquets top-level qu'on a écrits à la main.

**Générer le lock file avec pip-tools**, jamais à la main :

```bash
pip install pip-tools
# .in = source lisible, top-level uniquement, versions exactes
printf 'flask==3.1.3\n' > requirements.in
pip-compile --generate-hashes --allow-unsafe -o requirements.txt requirements.in
```

Pour un fichier dev (tests, lint) qui doit rester un `pip install --require-hashes -r dev-requirements.txt`
**seul sur la ligne** (donc lui aussi self-contained, sans dépendre d'un `-r requirements.txt`
imbriqué côté outillage) :

```bash
printf -- '-r requirements.in\npytest==8.4.2\npytest-cov==6.3.0\n' > dev-requirements.in
pip-compile --generate-hashes --allow-unsafe -o dev-requirements.txt dev-requirements.in
```

`-r requirements.in` (le `.in`, pas le `.txt`) dans le fichier dev fait resoudre pip-compile
flask + pytest + pytest-cov **ensemble** en un seul graphe cohérent, puis aplatit tout dans
`dev-requirements.txt` — pas de chaînage `-r` au runtime, un seul fichier autoportant.

**Toujours tester le lock file avant de le committer** — un `pip-compile` qui exécute sans
erreur ne garantit pas que `--require-hashes` passera (des extras/optional deps peuvent
échapper au graphe) :

```bash
python -m venv /tmp/verify && /tmp/verify/bin/pip install --only-binary=":all:" --require-hashes -r dev-requirements.txt
```

Garder le fichier `requirements.txt` (prod) **aussi** hash-locké même si le Dockerfile ne passe
pas `--require-hashes` explicitement : dès qu'une seule ligne du fichier a un hash, pip bascule
automatiquement en mode vérification pour tout le fichier — protection gratuite, zéro changement
de Dockerfile nécessaire.

## Actions tierces épinglées sur SHA complet, jamais sur un tag mutable (S7637)

Un tag comme `@v4` peut être déplacé par le mainteneur du repo (volontairement ou après
compromission de son compte) — épingler sur le SHA du commit rend la référence immuable.

```yaml
# ❌ — tag mutable
uses: actions/checkout@v4

# ✅ — SHA du commit, commentaire pour la lisibilité humaine
uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262  # v4.4.0
```

**Comment résoudre le SHA correct** (le tag `vX` seul ne suffit pas à savoir quel patch il
pointe) :

```bash
curl -s "https://api.github.com/repos/<owner>/<repo>/git/matching-refs/tags/v4." \
  | grep -oE '"ref": "refs/tags/[^"]+"|"sha": "[a-f0-9]{40}"' \
  | paste -d' ' - -
```

Vérifier que `"type": "commit"` (pas `"tag"`, ce qui signalerait un tag annoté dont le SHA
n'est pas directement utilisable) via :

```bash
curl -s "https://api.github.com/repos/<owner>/<repo>/git/refs/tags/vX.Y.Z"
```

**Rester dans la même ligne majeure** que celle déjà utilisée dans le workflow — une montée de
version majeure (ex. `docker/build-push-action` v6→v7) est un changement de comportement
potentiel, pas juste un pin de sécurité, et doit être proposée séparément (zéro refactoring
passant, cf. CLAUDE.md règle #3).

## Checklist avant commit d'un workflow

- [ ] Pas de `permissions:` au niveau `workflow` autre que `{}` (deny-all)
- [ ] Chaque job qui checkout/push/pull déclare son propre bloc `permissions` minimal
- [ ] Tout `pip install <paquet>` a `--only-binary=":all:"` (quoté)
- [ ] Toute version de paquet installée en CI est épinglée en exact (`==`), vérifiée résolvable
- [ ] Tout `pip install -r fichier.txt` a `--require-hashes`, et rien d'autre sur la même ligne
- [ ] `fichier.txt` généré via `pip-compile --generate-hashes`, testé en venv propre avant commit
- [ ] Tout `uses: owner/repo@vX` est un SHA complet avec commentaire `# vX.Y.Z`
- [ ] YAML validé (`python -c "import yaml; yaml.safe_load(open('...'))"`)
