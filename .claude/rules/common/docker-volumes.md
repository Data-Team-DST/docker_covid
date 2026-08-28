# Docker — volumes montés en écriture réelle (pas un sandbox de vérification)

Retour d'expérience (2026-08-28) : un `docker run` légitime — génération d'un vrai rapport
Evidently, une écriture réelle voulue dans le repo, pas une vérification/test couverte par
CLAUDE.md règle #9 — a monté `outputs/` en écriture (`-v $(pwd)/outputs:/app/outputs`) sans
`--user`. Les conteneurs tournant en root par défaut, les fichiers/dossiers créés sont devenus
`root:root` sur le volume. Conséquence, des runs plus tard : `dvc add`/`dvc status` lancés
depuis WSL (utilisateur non-root) ont échoué en `Permission denied` sur ces chemins — 258
sous-dossiers de `.dvc/cache/files/md5/` déjà pollués par des runs Docker antérieurs, plus
`outputs/drift/` lui-même.

## Règle

Tout `docker run` qui monte un répertoire du repo réel **en écriture** (donc hors sandbox de
vérification, cf. règle #9 — qui impose une copie jetable en lecture seule pour les tests) doit
passer `--user "$(id -u):$(id -g)"` (Linux/WSL), pour que les fichiers créés appartiennent à
l'utilisateur courant, pas à root — sauf besoin explicite et documenté de root dans le
conteneur.

```bash
# ❌ — fichiers/dossiers créés appartiendront à root, illisibles/inscriptibles ensuite
# depuis WSL par un utilisateur non-root
docker run --rm -v "$(pwd)/outputs:/app/outputs" mon-image python script.py

# ✅
docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd)/outputs:/app/outputs" mon-image python script.py
```

## Si la pollution existe déjà (contournement, pas une correction du fond)

Un fichier/dossier déjà root-owned sur un volume Windows monté en WSL (mode metadata) ne peut
pas être `chown`-é sans `sudo` (mot de passe requis, jamais disponible en session
non-interactive). Contournements validés :

- **Fichier/dossier isolé** : le recréer depuis PowerShell (côté Windows natif, qui ignore la
  couche de métadonnées WSL) — copie temporaire, suppression, recréation.
- **Opération DVC bloquée par `.dvc/cache` root-owned** : utiliser un DVC natif Windows (venv
  jetable, jamais installé dans le repo) plutôt que le binaire WSL — contourne entièrement la
  couche de métadonnées WSL responsable du blocage.

Ces deux contournements ne nettoient pas la pollution existante dans `.dvc/cache` (258
sous-dossiers concernés au 2026-08-28) — seulement le futur, via la règle ci-dessus.
