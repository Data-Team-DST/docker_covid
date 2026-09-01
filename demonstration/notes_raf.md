# Le pipeline DVC en détail (`dvc.yaml`, `params.yaml`, `dvc repro`)

7 stages, exécutés dans le container `trainer` (GPU), déclenchables individuellement ou en cascade via `dvc repro`. DVC ne relance que ce qui a changé (deps/params trackés par hash).

## Glossaire rapide

- **CLAHE** : égalisation d'histogramme adaptative (tuiles 8×8) et limitée en contraste (`clipLimit=2.0`) — améliore le contraste local sans sur-amplifier le bruit, contrairement à une égalisation globale.
- **Masking (ici)** : resize du mask (`INTER_NEAREST`, reste binaire) → `cv2.bitwise_and` (met à 0 tout ce qui n'est pas poumon) → crop+padding sur la zone non-nulle (`squared_crop_to_lungs`).
- **`.npy`** : format binaire natif NumPy (header + données brutes, pas de parsing texte), memory-mappable (`open_memmap`) — lisible/écrivable sans tout charger en RAM, d'où son usage massif ici vu le volume post-augmentation.

## Git ↔ DVC : comment le lien est géré dans ce projet

### Le principe

Git ne peut pas raisonnablement versionner 807 Mo de radiographies (`data/raw`, 42 355 fichiers) ni des modèles de plusieurs centaines de Mo — DVC prend le relais pour tout ce qui est gros/binaire, mais **le lien entre les deux reste Git**. Concrètement :

- **Git track** : le code, `dvc.yaml` (définition du pipeline), `dvc.lock` (état figé du pipeline — quel hash de donnée/code a produit quel résultat), `params.yaml`, et des **fichiers `.dvc`** (petits pointeurs texte, quelques lignes).
- **DVC track** : les données/modèles réels, adressés par leur hash MD5, stockés dans `.dvc/cache/` en local puis répliqués vers un remote distant (MinIO ou DagsHub).

### Le fichier pointeur `.dvc`

Exemple réel, `data/raw.dvc` (entièrement trackable par Git, ~6 lignes) :

```yaml
outs:
- md5: a918294d0bd698396493e00520a9cffa.dir
  size: 807555159
  nfiles: 42355
  hash: md5
  path: raw
```

Git ne voit que ce pointeur (un hash + des métadonnées) — jamais les 807 Mo réels. `data/raw/` lui-même est dans `.gitignore`. Quand quelqu'un clone le repo, il récupère ce pointeur instantanément, puis doit faire `dvc pull` pour rapatrier les vrais fichiers depuis le remote, en résolvant le hash.

Seuls deux `.dvc` sont trackés dans ce repo : `data/raw.dvc` et `outputs/drift/report.html.dvc` (le rapport de dérive Evidently — cas particulier : `/outputs/*` est ignoré globalement, sauf `!/outputs/drift/` ré-inclus explicitement dans `.gitignore` pour permettre au pointeur `.dvc` d'être trackable ; le vrai `report.html`, lui, reste ignoré via un `.gitignore` que DVC génère automatiquement dans `outputs/drift/`).

### `dvc.yaml` / `dvc.lock` — le pipeline versionné par Git

`dvc.yaml` décrit les 7 stages (deps/params/outs, déjà détaillé plus haut). `dvc.lock` est généré automatiquement par `dvc repro` — il fige, pour chaque stage, le hash exact de chaque dep/output à l'instant où le stage a tourné. C'est ce fichier qui permet à `dvc status`/`dvc repro` de savoir si un stage est à jour ou doit être rejoué (comparaison hash courant vs hash figé dans le lock). **`dvc.lock` est trackable par Git** — donc un `git log` sur ce fichier donne l'historique de "quelle version du pipeline a produit quel modèle".

### Les remotes (`.dvc/config`, trackable par Git — pas de secret dedans)

```
[core]
    remote = minio
[remote "minio"]        → s3://dvcstore, endpoint MinIO local (infra/docker-compose)
[remote "dagshub"]      → bucket S3-compatible DagsHub (partage équipe)
[remote "dagshub-storage"] → stockage natif DagsHub (prévisualisation sur dagshub.com)
```

Ce fichier ne contient que des **URLs**, aucun credential — safe à committer. Les credentials (access key MinIO, token DagsHub) vivent dans **`.dvc/config.local`**, généré par `make dvc-setup`/`dvc-setup-dagshub` à partir de `.env` — `.gitignore` l'exclut explicitement (`.dvc/config.local`), vérifié : jamais tracké, jamais apparu dans l'historique git de ce repo.

### Comment on pousse/tire les données ici

Pas de `dvc push`/`dvc pull` en ligne de commande directe dans ce projet — passe par :
- `make dvc-push` / `make dvc-pull` → MinIO (remote par défaut, dev local)
- `make dvc-push-dagshub` / `make dvc-pull-dagshub` → DagsHub (partage avec l'équipe)
- Le microservice **`dvc-service`** (port 5003, extrait de `data-service` — cf. plus haut sur les frontières de service) expose ces opérations en HTTP (`/v1/dvc/{status,pull,push,repro}`) pour le dashboard et les autres services, plutôt que d'exécuter la CLI `dvc` en local partout.
- `make dvc-repro` lance `dvc repro` **dans le container `trainer`** (GPU + dvc préinstallés) — pas besoin d'avoir dvc installé sur la machine hôte pour rejouer le pipeline complet.

## Branche classification

### 1. `augment` (`trainer/scripts/augment.py`)

`data/raw/COVID-19_Radiography_Dataset/{classe}/{images,masks}/` → `data/augmented/{train,test}/{classe}/{images,masks}/`

- Split train/test 80/20 par classe (stratifié de facto) fait **AVANT** augmentation, volontairement — sinon une image et sa variante augmentée (quasi-identique) pourraient tomber de part et d'autre du split, et le modèle "reconnaîtrait" en test des quasi-doublons vus à l'entraînement.

On augmente uniquement Train :

- Test = originaux uniquement, pas augmentés.
- Train = original + 3 `variants_per_image` (rotation, zoom, brightness, flip horizontal). Chaque variante est seedée par `(seed, class_label, idx, variante)` — reproductible déterministe par image, pas juste par run.

#### Augmentation des masks (`augment_pair()`, `ds_covid/augmentation.py`)

Le mask n'est pas augmenté indépendamment — il subit **exactement les mêmes tirages aléatoires** que l'image (même `rng`, un seul flip/angle/facteur de zoom tirés puis appliqués aux deux), pour rester aligné pixel-à-pixel avec l'image augmentée. Deux nuances importantes :

- **Interpolation différente selon le type de donnée** : l'image est ré-échantillonnée en `cv2.INTER_LINEAR` (interpolation lissée, adaptée à des niveaux de gris continus) ; le mask en `cv2.INTER_NEAREST` (plus proche voisin) pour **rester strictement binaire** — une interpolation linéaire créerait des valeurs intermédiaires floues aux bords du mask, incompatibles avec un mask de segmentation.
- **La luminosité n'affecte que l'image**, jamais le mask (`_adjust_brightness()` n'est appliqué qu'à `img_aug`) — logique, un mask binaire n'a pas de notion de luminosité.

### 2. `preprocess` (`preprocess.py`)

`data/augmented/` → `data/processed/{X,y}_{train,test}.npy`

- Pipeline par image (`ds_covid.preprocessing.process_single_image`) : denoising (opt.) → masking+crop (opt.) → CLAHE → resize → normalisation `[-1,1]`.
- Écrit directement en memmap disque (`numpy.lib.format.open_memmap`), jamais tout en RAM — nécessaire vu le volume (dizaines de milliers d'images post-augmentation).

### 3. `train` (`train.py`)

`X_train.npy`/`y_train.npy` → `data/models/classification.keras` + `outputs/metrics.json`

- Re-split interne train/val 85/15 (stratifié sur `y_train`) — soit un split final **train/val/test : 68/12/20** par rapport au dataset brut (détail des chiffres plus bas). `X_test`/`y_test` ne sont touchés qu'au stage `evaluate`, jamais vus par l'entraînement ni l'early stopping.
- `class_weight` "balanced" (`sklearn.compute_class_weight`) appliqué via `sample_weight` dans `MemmapSequence` plutôt que l'argument `class_weight=` de `model.fit()` — incompatible avec un `Sequence` custom sous Keras 3. La pondération ne s'applique qu'au train, pas au val (ne doit pas fausser `val_loss` surveillée par les callbacks).
- Callbacks : `EarlyStopping(patience=5, restore_best_weights=True)`, `ReduceLROnPlateau(factor=0.5, patience=3)`, `MlflowEpochLogger`.
- Tracking MLflow local + mirroring optionnel DagsHub (`DualMlflowRun`), modèle enregistré dans le Model Registry (`registered_model_name`).

### 4. `evaluate` (`evaluate.py`)

`classification.keras` + `X_test`/`y_test` → `outputs/evaluation_report.json` (accuracy, `classification_report` sklearn, matrice de confusion).

## Branche segmentation (parallèle, réutilise la sortie d'`augment`)

### 5. `preprocess_segmentation` (`preprocess_segmentation.py`)

Mêmes paires image/mask que `augment`, mais **pas** de masking/crop/CLAHE ici : le mask est la cible à prédire, pas une entrée. Sortie : `X_{train,test}.npy` (images) + `M_{train,test}.npy` (masks), même stratégie memmap.

### 6. `train_segmentation` (`train_segmentation.py`)

U-Net en 2 phases (freeze puis fine-tune).

- `ModelCheckpoint(monitor="val_loss", save_best_only=True)` réutilisé entre les 2 phases (une seule instance) — recréer l'instance à la phase 2 réinitialiserait `.best` à `+inf` et ferait perdre la comparaison avec le meilleur point de la phase 1 (`TODO.md #9`).

### 7. `evaluate_segmentation`

→ `outputs/segmentation_evaluation_report.json` — mesure la qualité **après** nettoyage du mask (voir ci-dessous), pas sur la sortie brute du U-Net.

### Dice et IoU — les deux métriques de qualité du mask

Les deux comparent le mask prédit (binaire, 0/1 par pixel) au mask vérité terrain, pixel par pixel. Notations : `∩` = intersection (pixels à 1 dans les deux masks), `∪` = union (pixels à 1 dans au moins un des deux).

- **IoU** (*Intersection over Union*, aussi appelé indice de Jaccard) : `IoU = ∩ / ∪`. Le plus intuitif — proportion de la zone combinée des deux masks qui est effectivement partagée.
- **Dice** (coefficient de Sørensen-Dice) : `Dice = 2·∩ / (|mask_pred| + |mask_vérité|)`. Même idée, mais compte l'intersection deux fois au numérateur plutôt que d'utiliser l'union — ça pénalise moins durement les petits désaccords de contour que l'IoU. C'est la métrique choisie ici comme critère d'arrêt (`params.yaml § min_val_dice: 0.5`, `evaluate.py`) et comme loss d'entraînement (`dice_loss = 1 - dice_coef`, combinée à la BCE — voir plus bas).

Les deux valent 1.0 pour un mask parfait, 0.0 si aucun pixel ne se recouvre. Dice ≥ IoU toujours (relation mathématique directe entre les deux formules) — ne pas comparer un score Dice à un seuil pensé pour l'IoU ou l'inverse.

Implémentation réelle (`ds_covid/segmentation.py::dice_coef` / `iou_metric`) : un `smooth = 1.0` est ajouté au numérateur et au dénominateur des deux formules — évite une division par zéro si vérité terrain ET prédiction sont entièrement vides (aucun pixel poumon), et lisse légèrement le score sur les petits masks.

`evaluate_segmentation.py` calcule ces deux métriques deux fois : une fois sur le mask brut (sortie sigmoïde du U-Net directement seuillée à 0.5), une fois sur le mask nettoyé (`clean_mask()`, voir juste en dessous) — pour objectiver le gain apporté par le nettoyage.

## Nettoyage du mask prédit (`clean_mask()`)

Le U-Net brut produit un mask bruité : des îlots de pixels isolés hors des poumons (faux positifs ponctuels) et/ou des petits trous à l'intérieur de la silhouette pulmonaire. Sans nettoyage, ces défauts se propagent au recadrage backend (`squared_crop_to_lungs()`, qui borne sur *tout pixel non nul* du mask) — un îlot parasite loin des poumons élargirait artificiellement la bounding box du crop.

Deux étapes (`clean_mask()`, `trainer/src/ds_covid/segmentation.py`, dupliquée à l'identique dans `segmentation-service/src/segmentation_service/model.py` pour l'inférence) :

1. **Composantes connexes** (`cv2.connectedComponentsWithStats`, connectivity=8) → garde les `clean_mask_components: 2` plus grandes composantes par aire (poumon gauche + droit) → élimine les îlots parasites.
2. **Fermeture morphologique** (`cv2.morphologyEx(MORPH_CLOSE)`, noyau elliptique `clean_mask_closing_kernel: 15`) → comble les petits trous internes sans déformer le contour.

Même valeurs utilisées au stage `evaluate_segmentation` et à l'inférence réelle (`segmentation-service`) — mais **dupliquées** entre `params.yaml` et `segmentation-service/config.py::Settings` (codées en dur côté service). Point de vigilance similaire au bug CLASS_NAMES déjà corrigé : si l'une change sans l'autre, le nettoyage diverge silencieusement entre entraînement/évaluation et inférence.

## Architecture des deux modèles

### Classification — `classification.keras` (`ds_covid/models.py`, from scratch)

- Entrée 256×256×1 → 4× (`Conv2D` → `BatchNorm` → `MaxPool`), 32/64/128/256 filtres → `GlobalAveragePooling2D` → `Dense(128, relu)` → `Dropout(0.5)` → `Dense(4, softmax)`.
- Loss `sparse_categorical_crossentropy`. Entraîné entièrement from scratch (pas de transfer learning).
- `class_weight` "balanced" (dataset déséquilibré : 10192 Normal vs 1345 Viral Pneumonia).

### Segmentation — `segmentation.keras` (`ds_covid/segmentation.py`, transfer learning)

- Encoder **MobileNetV2 pré-entraîné ImageNet** (canal grayscale dupliqué ×3 pour matcher l'entrée RGB attendue) + decoder codé à la main (`Conv2DTranspose` + 4 skip connections).
- Loss `binary_crossentropy + dice_loss`.
- Entraînement en 2 phases : **freeze** (encoder gelé, 8 epochs, lr 1e-3) puis **fine-tune** (encoder dégelé, 25 epochs, lr 1e-5 — très bas pour ne pas détruire les poids ImageNet).

### Rappel — c'est quoi un U-Net ?

Architecture encoder/decoder en forme de "U" (Ronneberger et al., 2015, imagerie biomédicale à l'origine) :

- **Encoder** (chemin descendant) : downsampling progressif, extrait des features de plus en plus abstraites en perdant de la résolution spatiale — comme un CNN classique.
- **Decoder** (chemin montant) : upsampling progressif pour reconstruire une sortie à la résolution d'origine (ici, un mask pixel par pixel).
- **Skip connections** (l'idée clé) : chaque niveau de l'encoder est directement connecté (concaténé) au niveau correspondant du decoder, en plus du flux principal via le bottleneck. Sans ça, le decoder ne repartirait que du bottleneck — trop compressé pour reconstruire des contours précis. Les skip connections réinjectent le détail spatial fin (bords, contours) perdu pendant la descente.
- Ici, l'encoder n'est pas entraîné from scratch comme dans le papier original : c'est un MobileNetV2 pré-entraîné (transfer learning) — même principe d'architecture en U, mais on réutilise des features ImageNet déjà apprises plutôt que de tout apprendre depuis zéro.

### Décoder les noms : "Up" et "block_N_expand_relu"

**"Up"** = **upsampling**, l'opération qui augmente la résolution spatiale — l'inverse du `MaxPooling` de l'encoder. Implémenté ici par `Conv2DTranspose` : contrairement à un simple resize/interpolation, c'est une convolution transposée dont l'upsampling est **appris** (poids entraînables), pas une interpolation géométrique fixe. Chaque `Conv2DTranspose(strides=2)` double la résolution : 8×8 → 16×16 → 32×32 → 64×64 → 128×128 → 256×256, symétrique à la descente de l'encoder.

Donc "Up + concat skip1 + 2×Conv2D" = 3 étapes en séquence à chaque niveau du decoder :
1. **Up** (`Conv2DTranspose`) — double la résolution
2. **+ concat skip1** — recolle le détail spatial de l'encoder à ce niveau (la skip connection)
3. **+ 2×Conv2D** — deux convolutions classiques pour fusionner/affiner après la concaténation

**"block_N_expand_relu"** = nom de layer interne à **MobileNetV2** (nommage Keras officiel, pas choisi par nous). MobileNetV2 empile des blocs "inverted residual", chacun structuré en 3 étapes : **expand** (conv 1×1 qui augmente les canaux) → **depthwise** (conv 3×3 par canal) → **project** (conv 1×1 qui réduit les canaux). `block_N_expand_relu` = l'activation ReLU6 juste après la conv d'expansion du bloc n°N.

Pourquoi ces 4 layers précisément (`block_1/3/6/13_expand_relu`) sont choisis comme points de skip : ce sont les **dernières activations à pleine résolution juste avant chaque downsampling** (stride 2) du réseau — le point idéal pour une skip connection, puisque la résolution y correspond exactement à ce que le decoder doit retrouver à la remontée.

### Rôle de chaque callback

| Callback | Rôle |
|---|---|
| **`EarlyStopping`** | Arrête l'entraînement si `val_loss` ne s'améliore plus après `patience` epochs — évite l'overfitting et le temps perdu. `restore_best_weights=True` : à l'arrêt, recharge les poids de la meilleure epoch, pas la dernière. Patience différente par phase en segmentation (3 en freeze, 4 en fine-tune — le fine-tuning est plus lent à converger, on lui laisse plus de marge). |
| **`ReduceLROnPlateau`** | Diminue le learning rate (`factor=0.5`) quand `val_loss` stagne pendant `patience` epochs, sans attendre l'arrêt complet — permet de continuer à progresser à petits pas quand le LR courant est trop grand pour affiner davantage. `min_lr` plafonne la descente. |
| **`ModelCheckpoint`** | Sauvegarde sur disque le modèle à chaque fois que `val_loss` s'améliore (`save_best_only=True`). En segmentation, **une seule instance réutilisée entre les 2 phases** — recréer l'instance à la phase 2 réinitialiserait `.best` à `+inf` et ferait perdre la comparaison avec la phase 1. |
| **`MlflowEpochLogger`** (callback maison) | Logue les métriques Keras de chaque epoch dans MLflow (local + DagsHub) au fil de l'entraînement plutôt qu'un seul résumé final — permet de suivre la courbe en temps réel dans l'UI MLflow. `step_offset` en phase 2 pour garder une timeline continue avec la phase 1. |
| **`TqdmCallback`** | Barre de progression lisible en console (juste UX, aucun effet sur l'entraînement). |

### Rôle de chaque couche

**Classification (CNN, `build_cnn`)**

| Couche | Rôle |
|---|---|
| `Conv2D` | Extrait des motifs locaux (bords, textures) via des filtres convolutifs — 32→64→128→256 filtres, de plus en plus abstraits en profondeur. |
| `BatchNormalization` | Normalise les activations entre les couches (moyenne 0, variance 1) — stabilise et accélère l'entraînement, réduit la sensibilité à l'initialisation. |
| `MaxPooling2D` | Sous-échantillonne (÷2 en largeur/hauteur) en gardant le maximum local — réduit la résolution spatiale, apporte une invariance aux petites translations, diminue le coût de calcul en aval. |
| `GlobalAveragePooling2D` | Réduit chaque carte de features `(H,W,C)` à un seul vecteur `(C,)` en moyennant spatialement — remplace un `Flatten()+Dense` classique, beaucoup moins de paramètres, moins d'overfitting. |
| `Dense(128, relu)` | Couche entièrement connectée — combine les features globales extraites avant la décision finale. |
| `Dropout(0.5)` | Désactive aléatoirement 50% des neurones à chaque step d'entraînement — régularisation, force le réseau à ne pas dépendre de neurones spécifiques. |
| `Dense(4, softmax)` | Couche de sortie — 4 logits convertis en probabilités qui somment à 1 (une par classe). |

**Segmentation (U-Net, `build_unet`)**

| Couche | Rôle |
|---|---|
| `Concatenate([inputs]×3)` | Duplique le canal grayscale en 3 canaux — MobileNetV2 attend une entrée RGB (poids ImageNet entraînés sur 3 canaux). |
| `MobileNetV2` (encoder) | Bloc pré-entraîné entier servant d'encoder — extrait les features à 5 niveaux de résolution (dont les 4 points de skip). |
| `Conv2DTranspose` | Convolution transposée — **upsampling appris** (×2 résolution), l'inverse du MaxPooling, mais avec des poids entraînables plutôt qu'une simple interpolation. |
| `Concatenate([x, skip])` | Les skip connections — réinjecte le détail spatial fin de l'encoder dans le decoder (cf. rappel U-Net ci-dessus). |
| `Conv2D` (×2 par niveau decoder) | Affine les features après chaque concaténation skip, avant l'upsampling suivant. |
| `Conv2DTranspose(1, sigmoid)` finale | Sortie — upsampling final vers la résolution d'entrée + activation sigmoid pour une probabilité par pixel (poumon vs fond). |

## Chiffres du pipeline

⚠️ `dvc status` indique que les fichiers `outputs/*.json` actuellement sur disque sont **périmés** (`preprocess.max_samples_per_class: modified`, `data/raw: modified`) — générés avec un échantillon réduit (probablement un smoke-test à ~50 images/classe : 640 train / 40 test au total), pas avec le dataset complet actuel. Un `dvc repro` complet n'a pas encore été rejoué depuis.

Estimation calculée à partir des vraies valeurs connues — dataset brut = 21 165 images (`DEFAULT_CLASS_COUNTS`, confirmé par `dvc.lock` : `data/raw` = 42 355 fichiers = 21 165 images × 2, chaque image ayant son mask) :

| Classe | Brut | Train raw (80%) | Test (20%, jamais augmenté) | Train augmenté (×4) |
|---|---|---|---|---|
| COVID | 3 616 | ≈ 2 893 | ≈ 723 | ≈ 11 572 |
| Normal | 10 192 | ≈ 8 154 | ≈ 2 038 | ≈ 32 616 |
| Viral Pneumonia | 1 345 | ≈ 1 076 | ≈ 269 | ≈ 4 304 |
| Lung_Opacity | 6 012 | ≈ 4 810 | ≈ 1 202 | ≈ 19 240 |
| **Total** | **21 165** | **≈ 16 933** | **≈ 4 233** | **≈ 67 732** |

Puis split train/val (85/15) sur les 67 732 augmentées :

- **Train final ≈ 57 572** (68% du brut)
- **Val ≈ 10 160** (12% du brut)
- **Test = 4 233** (20% du brut, fixe — jamais affecté par l'augmentation)

Ces chiffres sont une estimation cohérente avec `params.yaml` et le dataset actuel, pas une mesure directe — à confirmer par un `dvc repro` complet (long, GPU) qui donnera les vrais totaux à quelques unités près (arrondis de `train_test_split`).
