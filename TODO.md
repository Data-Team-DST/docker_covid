# TODO — points en attente

Ouvert le 2026-08-26, suite au chantier de réorganisation architecture
(`CHANTIER_ARCHITECTURE.md`) et à l'intégration du merge `raf5` (segmentation U-Net).
Chaque point ci-dessous a été identifié en session mais volontairement laissé de côté
(décision à prendre, hors périmètre du moment, ou correction non triviale).

## Décisions en attente

### 1. `backend/requirements-dev.txt` — tensorflow manquant, `make test` bloqué

`backend/app/features/preprocessing.py` importe désormais `ds_covid.segmentation`
(ajouté par le merge `raf5`), qui importe `tensorflow` au niveau module. Le venv de test
backend est volontairement **"sans tensorflow"** (choix de conception : venv plus léger/
rapide, cf. commentaire `Makefile` cible `setup-be`). Ce choix n'est plus tenable tel quel.

Options envisagées (aucune tranchée) :
- Ajouter `tensorflow==2.18.0` + `opencv-python-headless==4.10.0.84` à
  `backend/requirements-dev.in` et régénérer le lockfile (`pip-compile --generate-hashes`,
  en conteneur Linux — jamais sur cette machine Windows) → venv de test backend devient
  aussi lourd que celui de `trainer/`.
- Import paresseux de `tensorflow` dans `trainer/src/ds_covid/segmentation.py` (à l'intérieur
  des fonctions qui en ont besoin, pas au niveau module) → garde le venv de test léger, mais
  touche au code de Rafael.

**Tant que ce point n'est pas tranché, `make test` échoue à la collecte des tests
(`backend/tests/unit/{test_api,test_predict,test_preprocessing,test_security}.py`).**

## Vérifications non faites

### 2. `dvc dag` / `dvc repro` jamais lancés

La cohérence du graphe `dvc.yaml` après les déplacements (`scripts/` → `trainer/scripts/`,
`backend/src/ds_covid` → `trainer/src/ds_covid`) n'a été vérifiée que statiquement (lecture,
`yaml.safe_load`). Un `dvc dag` (léger, ne nécessite pas les données) confirmerait que DVC
résout bien tous les chemins. Un `dvc repro` complet est plus lourd (pipeline sur 42 330
images) et rejouera les 4 stages originaux malgré un contenu identique, puisque le hash des
deps DVC inclut le chemin.

## Bugs signalés, non corrigés (hors périmètre du moment)

### 3. `ops/check_quality.sh` — scanne `frontend/.venv`, crash sur fichier mal encodé

`make lint-full` (dépend de `setup-fe`) crée `frontend/.venv`, que le check de structure/
code-smell de `check_quality.sh` scanne sans l'exclure (aucun filtre `.venv` dans son
parcours de `frontend/`). Deux symptômes : faux positifs "arborescence trop profonde" sur
les paquets installés, et un `UnicodeDecodeError` qui fait planter `make lint-full` sur un
fichier `.py` mal encodé quelque part dans `frontend/.venv/lib/.../site-packages/`.
Reproductible sur toute machine où `frontend/.venv` existe localement.

### 4. 4 findings `ruff` mineurs (code du merge `raf5`, auto-fixables)

```
backend/app/config.py:3:1: I001 [*] Import block is un-sorted or un-formatted
backend/app/config.py:47:23: UP045 [*] Use `X | None` for type annotations
backend/app/features/preprocessing.py:74:25: UP045 [*] Use `X | None` for type annotations
backend/app/features/preprocessing.py:80:23: UP045 [*] Use `X | None` for type annotations
```

`ruff check --fix` les corrige automatiquement — pas fait, pour ne pas toucher au code de
Rafael sans qu'il ait été audité au préalable (voir point 5).

### 5. Nombreuses lignes >88 caractères dans le code du merge `raf5`

`predict.py`, `config.py`, `features/preprocessing.py`, `models/loader.py` — dépassent la
limite `pylint` (`max-line-length = 88`, `pyproject.toml`). `ruff` les ignore (E501 exclu du
projet), mais `pylint`/`make lint-full` les signalerait. Préexistant au merge, pas introduit
par le chantier de réorganisation.

## Audit qualité du refactor de Rafael (segmentation U-Net, branche `raf5`)

Demandé par Steven le 2026-08-26, fait par l'agent `mle-reviewer` (lecture seule). Le point
bloquant a été corrigé immédiatement (voir "Fait" ci-dessous) ; les autres restent ouverts.

### 7. [IMPORTANT] `ModelCheckpoint` recréé à chaque phase — perte de comparaison inter-phases

`trainer/scripts/train_segmentation.py:100-104` (phase 1) et `:127-131` (phase 2) : chaque
`model.fit()` reçoit une **nouvelle** instance de `ModelCheckpoint(..., save_best_only=True)`
— Keras réinitialise son "best" interne à +inf à chaque instanciation, donc la phase 2 ne
sait rien du meilleur point de la phase 1. Si le fine-tuning complet démarre moins bien que
la phase 1 (risque explicitement documenté dans le docstring du fichier, ligne 8 : "le
val_dice s'effondre en 1-2 epochs si on dégèle tout dès le début"), la 1ère epoch de phase 2
écrase quand même `model_path` sans comparaison avec le vrai meilleur des deux phases.
Fix : réutiliser la même instance de callback entre les deux `fit()` (Keras conserve
`.best`), ou l'initialiser manuellement avec la meilleure val_loss de phase 1.

### 8. [IMPORTANT] Métriques loguées MLflow potentiellement différentes du modèle sauvegardé

`trainer/scripts/train_segmentation.py:135-138` logue `val_dice`/`val_iou`/`val_loss` de la
**dernière** epoch de la phase 2, mais `EarlyStopping(restore_best_weights=True)` restaure
en mémoire les poids de la **meilleure** epoch (pas forcément la dernière), et
`model.load_weights(model_path)` (ligne 144, juste avant le log MLflow) recharge encore un
troisième état possible (sujet au bug du point 7). Le nombre affiché comme "val_dice" du run
MLflow ne décrit donc pas fiablement l'artefact réellement enregistré dans le Model Registry.
Fix : recalculer dice/iou APRÈS `model.load_weights(model_path)`, juste avant de logger
(`evaluate_segmentation.py` le fait déjà correctement sur le test set — même logique
manquante ici sur le val set).

### 9. [IMPORTANT] Aucun test sur les fonctions ML cœur de la segmentation

Zéro test unitaire sur `dice_coef`, `dice_loss`, `combined_loss`, `iou_metric`, `clean_mask`,
`collect_pairs`, `load_pair` (`trainer/src/ds_covid/segmentation.py`) ni sur `MemmapSequence`
(`trainer/src/ds_covid/data.py`) — aucun `trainer/tests/` n'existe. Une régression silencieuse
(signe inversé dans `dice_loss`, off-by-one dans `clean_mask`) ne serait détectée par rien
avant un `dvc repro` complet sur les 42k images.
Fix : `trainer/tests/test_segmentation.py` avec masks synthétiques (dice=1 sur masks
identiques, dice=0 sur masks disjoints, `clean_mask` qui élimine bien un îlot parasite).

### 10. [IMPORTANT] Comportement fail-closed de `/predict` et mask vide non testés (backend)

`backend/app/api/predict.py:69-76` (503 si masking actif sans modèle segmentation chargé) et
`backend/app/api/health.py` (`segmentation_model_loaded`) : aucun test n'exerce ni le 503 ni
ce champ. Par ailleurs un mask prédit vide (image atypique) fait lever une `ValueError` dans
`squared_crop_to_lungs` (`trainer/src/ds_covid/preprocessing.py:41`), capturée par le
`except Exception` générique de `predict.py:132-136` → 500 générique jamais testé, qui masque
une condition client légitime derrière un code d'erreur suggérant un bug serveur.
Fix : test avec `segmentation_model_loader.is_loaded=False` + `masking=True` → 503 attendu ;
test avec mask entièrement vide → vérifier une erreur explicite (422 plutôt que 500 générique).

### 11. [MOYEN] Duplication `params.yaml` / `backend/app/config.py` — img_size partagé entre 2 modèles

`img_size`/`masking`/`cropping`/`clahe*`/`denoising_method`/`clean_mask_*`
(`backend/app/config.py:41-49`) sont dupliqués à la main depuis `params.yaml` — cohérents
aujourd'hui par inspection, rien ne garantit qu'ils le restent au prochain réentraînement.
Plus précisément, `settings.img_size` sert à la fois de résolution finale classifieur ET de
résolution d'entrée attendue par le U-Net — un futur réentraînement avec des tailles
différentes casserait l'inférence *en silence* (mask mal redimensionné, pas d'erreur).
Fix : test qui charge `params.yaml` et vérifie l'égalité avec les defaults de `Settings`, ou
mieux, source unique (Settings lit `params.yaml` au lieu de dupliquer les valeurs en dur).

### 12. [MOYEN] Aucune passerelle de promotion sur l'évaluation du U-Net

`trainer/scripts/train_segmentation.py:145` enregistre le modèle dans le MLflow Model
Registry quelle que soit la qualité mesurée — pas de seuil minimum dice/iou, pas de
comparaison au modèle en prod. Même manque que sur le pipeline de classification (pas une
régression de cette feature, mais étendue plutôt que corrigée).

### 13. [NOTE] Couplage backend/trainer via `ds_covid` — à surveiller, pas bloquant

`backend/app/features/preprocessing.py` importe `ds_covid` (embarqué par `COPY` au build de
l'image backend, pas un appel réseau à runtime — ne viole pas R8 au sens strict). Mais c'est
un couplage de build réel : toute modification de `ds_covid.preprocessing`/`segmentation`
côté `trainer/` impacte silencieusement le backend au prochain build, sans test croisé qui
le garantisse (lié au point 11).

`train_segmentation.ipynb` vérifié : aucune fuite (pas de token/chemin local sensible en
sortie de cellule — juste des chemins Google Colab génériques `/content/...`).

## Fait — pour mémoire (ne pas rouvrir sans raison)

- `ops/data/{models,processed}/.gitkeep` accidentels → supprimés (`20ef63e`)
- Incohérence volume streamlit `/app/frontend` vs `WORKDIR /workspace` → corrigée (`2b1e65d`)
- Merge `raf5` intégré, conflit `backend/Dockerfile` résolu → `1bd8474`
- Bug démarrage backend (`lifespan` dupliqué sans import `asynccontextmanager`) → corrigé
  dans `1bd8474`
- `ds_covid` introuvable en local hors Docker (fallback `sys.path`) → corrigé (`08bb097`)
- Règle CLAUDE.md #9 précisée (copie sandbox ciblée, jamais par exclusion) → `650d596`
- **[BLOQUANT]** `MemmapSequence` dupliquée dans `trainer/scripts/train.py` écrasait l'import
  `ds_covid.data.MemmapSequence` (fix déjà validé par Steven sur `raf5`, commit `dbe7415`,
  jamais rapatrié dans le merge) → réappliqué (`2c16d01`)
