# Guide d'Utilisation des Transformateurs d'Images

Ce guide présente l'utilisation des transformateurs pour le traitement d'images médicales dans le cadre du projet COVID-19 Radiography.

---

## 📚 Table des Matières

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Architecture Générale](#architecture-générale)
4. [Transformateurs Disponibles](#transformateurs-disponibles)
   - [Image Loaders](#1-image-loaders)
   - [Image Preprocessing](#2-image-preprocessing)
   - [Image Augmentation](#3-image-augmentation)
   - [Image Features](#4-image-features)
   - [Utilities](#5-utilities)
5. [Pipelines Complets](#pipelines-complets)
6. [Exemples Pratiques](#exemples-pratiques)
7. [Bonnes Pratiques](#bonnes-pratiques)
8. [Troubleshooting](#troubleshooting)

---

## Introduction

Les transformateurs suivent l'API **scikit-learn** avec les méthodes standard :
- `fit(X, y=None)` : Apprentissage des paramètres (si nécessaire)
- `transform(X)` : Application de la transformation
- `fit_transform(X, y=None)` : Combinaison de fit et transform

Tous les transformateurs sont compatibles avec `sklearn.pipeline.Pipeline`.

---

## Installation

```python
# Import des transformateurs
from src.features.Pipelines.transformateurs import (
    # Loaders
    ImageLoader,
    # Preprocessing
    ImageResizer,
    ImageNormalizer,
    ImageMasker,
    ImageFlattener,
    ImageBinarizer,
    # Augmentation
    ImageAugmenter,
    ImageRandomCropper,
    # Features
    ImageHistogram,
    ImagePCA,
    ImageStandardScaler,
    # Utilities
    VisualizeTransformer,
    SaveTransformer,
)
```

---

## Architecture Générale

### Flux de Traitement Typique

```
Chemins fichiers → ImageLoader → Preprocessing → Augmentation → Feature Extraction → ML Model
                         ↓             ↓              ↓                ↓
                    PIL Images    NumPy Arrays   NumPy Arrays    Feature Vectors
```

### Formats de Données

| Étape | Input | Output |
|-------|-------|--------|
| **ImageLoader** | `List[str]` (chemins) | `List[PIL.Image]` |
| **ImageResizer** | `List[PIL.Image]` ou `np.ndarray` | `np.ndarray` (N, H, W) |
| **ImageNormalizer** | `np.ndarray` | `np.ndarray` (normalisé) |
| **ImageFlattener** | `np.ndarray` (N, H, W) | `np.ndarray` (N, H×W) |
| **ImagePCA** | `np.ndarray` | `np.ndarray` (N, n_components) |

---

## Transformateurs Disponibles

## 1. Image Loaders

### `ImageLoader`

Charge des images depuis des chemins de fichiers et les convertit en niveaux de gris.

#### Paramètres

```python
ImageLoader(
    img_size=(128, 128),      # Taille cible (pour compatibilité)
    color_mode='L',           # 'L' = grayscale, 'RGB' = couleur
    validate_paths=True,      # Validation des chemins avant chargement
    fail_on_error=False,      # Lève une exception si erreur de chargement
    verbose=True              # Affiche la progression
)
```

#### Exemple d'utilisation

```python
from pathlib import Path

# Liste des chemins d'images
image_paths = [
    "data/raw/COVID-19_Radiography_Dataset/COVID-19_Radiography_Dataset/COVID/images/COVID-1.png",
    "data/raw/COVID-19_Radiography_Dataset/COVID-19_Radiography_Dataset/COVID/images/COVID-2.png",
]

# Chargement
loader = ImageLoader(color_mode='L', verbose=True)
images = loader.transform(image_paths)

# Vérifier les images chargées
print(f"Images chargées: {loader.n_images_loaded_}")
print(f"Échecs: {len(loader.failed_images_)}")
```

#### Attributs après transformation

- `n_images_loaded_` : Nombre d'images chargées avec succès
- `failed_images_` : Liste des chemins ayant échoué

---

## 2. Image Preprocessing

### `ImageResizer`

Redimensionne les images à une taille cible.

#### Paramètres

```python
ImageResizer(
    img_size=(256, 256),           # Taille cible (width, height)
    resample=RESAMPLE_LANCZOS,     # Algorithme de rééchantillonnage
    preserve_aspect_ratio=False,   # Préserver le ratio d'aspect
    verbose=True
)
```

#### Exemple d'utilisation

```python
# Redimensionnement standard
resizer = ImageResizer(img_size=(224, 224))
images_resized = resizer.fit_transform(images)

# Avec préservation du ratio d'aspect
resizer_aspect = ImageResizer(
    img_size=(256, 256),
    preserve_aspect_ratio=True
)
images_padded = resizer_aspect.fit_transform(images)
```

#### Comportement

- **Sans préservation** : Étire l'image pour remplir exactement `img_size`
- **Avec préservation** : Redimensionne proportionnellement et ajoute du padding noir

---

### `ImageNormalizer`

Normalise les valeurs de pixels selon différentes méthodes.

#### Paramètres

```python
ImageNormalizer(
    method='minmax',              # 'minmax', 'standard', ou 'custom'
    feature_range=(0.0, 1.0),     # Plage pour minmax/custom
    per_image=False,              # Normalisation par image ou globale
    verbose=True
)
```

#### Méthodes de normalisation

| Méthode | Formule | Usage |
|---------|---------|-------|
| **minmax** | `(X - min) / (max - min)` | Normalisation [0, 1] |
| **standard** | `(X - mean) / std` | Z-score standardization |
| **custom** | Minmax puis scale vers `feature_range` | Plage personnalisée |

#### Exemple d'utilisation

```python
# Normalisation globale (statistiques sur tout le dataset)
normalizer = ImageNormalizer(method='minmax', per_image=False)
normalizer.fit(images_train)  # Calcule min/max sur l'ensemble
images_norm = normalizer.transform(images_train)
images_test_norm = normalizer.transform(images_test)  # Utilise les mêmes stats

# Normalisation par image (chaque image indépendamment)
normalizer_per_img = ImageNormalizer(method='standard', per_image=True)
images_standardized = normalizer_per_img.fit_transform(images)

# Normalisation custom vers [-1, 1]
normalizer_custom = ImageNormalizer(
    method='custom',
    feature_range=(-1.0, 1.0)
)
images_custom = normalizer_custom.fit_transform(images)
```

---

### `ImageMasker`

Applique des masques binaires pour isoler les régions d'intérêt (ROI).

#### Paramètres

```python
from src.features.Pipelines.transformateurs.image_preprocessing import MaskerConfig

config = MaskerConfig(
    mask_threshold=0.5,    # Seuil de binarisation du masque
    resize_masks=True,     # Redimensionner les masques si nécessaire
    invert_mask=False,     # Inverser le masque
    verbose=True
)

ImageMasker(
    mask_paths=list_of_mask_paths,
    config=config
)
```

#### Exemple d'utilisation

```python
# Chemins des masques (même ordre que les images)
mask_paths = [
    "data/raw/COVID-19_Radiography_Dataset/COVID-19_Radiography_Dataset/COVID/masks/COVID-1.png",
    "data/raw/COVID-19_Radiography_Dataset/COVID-19_Radiography_Dataset/COVID/masks/COVID-2.png",
]

# Application des masques
masker_config = MaskerConfig(mask_threshold=0.5, resize_masks=True)
masker = ImageMasker(mask_paths=mask_paths, config=masker_config)
images_masked = masker.fit_transform(images)
```

#### ⚠️ Important

- Le nombre de masques **doit correspondre** au nombre d'images
- Les masques sont automatiquement binarisés avec `mask_threshold`
- Utilisé pour analyser uniquement les poumons dans les radiographies

---

### `ImageFlattener`

Aplatit les images en vecteurs 1D pour les modèles ML traditionnels.

#### Paramètres

```python
ImageFlattener(
    order='C',      # 'C' = row-major, 'F' = column-major
    verbose=True
)
```

#### Exemple d'utilisation

```python
# Aplatissement
flattener = ImageFlattener()
X_flat = flattener.fit_transform(images)  # Shape: (n_samples, height × width)

print(f"Shape originale: {images.shape}")
print(f"Shape aplatie: {X_flat.shape}")
print(f"Nombre de features: {flattener.n_features_}")

# Reconstruction
images_reconstructed = flattener.inverse_transform(X_flat)
```

#### Utilisation typique

```python
# Pipeline pour Random Forest ou SVM
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier

pipeline = Pipeline([
    ('flatten', ImageFlattener()),
    ('classifier', RandomForestClassifier())
])

pipeline.fit(images_train, labels_train)
```

---

### `ImageBinarizer`

Binarise les images avec différentes méthodes de seuillage.

#### Paramètres

```python
ImageBinarizer(
    threshold=0.5,           # Valeur de seuil ou méthode ('mean', 'median', 'otsu')
    invert=False,            # Inverser la binarisation
    output_dtype=np.float32,
    verbose=True
)
```

#### Méthodes de seuillage

| Méthode | Description |
|---------|-------------|
| **Valeur fixe** (ex: 0.5) | Seuil manuel |
| **'mean'** | Seuil = moyenne des pixels |
| **'median'** | Seuil = médiane des pixels |
| **'otsu'** | Seuil optimal selon la méthode d'Otsu |

#### Exemple d'utilisation

```python
# Seuil fixe
binarizer = ImageBinarizer(threshold=0.5)
images_binary = binarizer.fit_transform(images)

# Seuil adaptatif (Otsu)
binarizer_otsu = ImageBinarizer(threshold='otsu')
images_otsu = binarizer_otsu.fit_transform(images)

print(f"Seuil calculé par Otsu: {binarizer_otsu.threshold_value_}")

# Binarisation inversée
binarizer_inv = ImageBinarizer(threshold='mean', invert=True)
images_inv = binarizer_inv.fit_transform(images)
```

---

## 3. Image Augmentation

### `ImageAugmenter`

Applique diverses techniques d'augmentation pour enrichir le dataset.

#### Paramètres

```python
ImageAugmenter(
    flip_horizontal=True,              # Flip horizontal aléatoire
    flip_vertical=False,               # Flip vertical aléatoire
    rotation_range=0,                  # Rotation max en degrés (0 = désactivé)
    brightness_range=None,             # (min, max) multiplicateurs de luminosité
    noise_std=0.0,                     # Écart-type du bruit gaussien
    zoom_range=None,                   # (min, max) facteurs de zoom
    probability=0.5,                   # Probabilité d'augmentation par image
    seed=None,                         # Graine aléatoire pour reproductibilité
    verbose=True
)
```

#### Exemple d'utilisation

```python
# Augmentation modérée
augmenter = ImageAugmenter(
    flip_horizontal=True,
    rotation_range=15,           # ±15 degrés
    brightness_range=(0.8, 1.2), # ±20% luminosité
    probability=0.5,
    seed=42
)
images_aug = augmenter.fit_transform(images)

print(f"Images augmentées: {augmenter.n_images_augmented_}/{len(images)}")

# Augmentation agressive pour classes minoritaires
augmenter_aggressive = ImageAugmenter(
    flip_horizontal=True,
    flip_vertical=True,
    rotation_range=30,
    brightness_range=(0.7, 1.3),
    noise_std=0.01,
    zoom_range=(0.9, 1.1),
    probability=0.8,
    seed=42
)
images_aug_heavy = augmenter_aggressive.fit_transform(minority_class_images)
```

#### 💡 Conseil pour dataset déséquilibré

Pour la classe **Viral Pneumonia** (1,345 images) :

```python
# Augmenter jusqu'à ~6000 images
n_target = 6000
n_current = 1345
n_repeats = n_target // n_current  # ~4 répétitions

images_augmented = []
for _ in range(n_repeats):
    aug = ImageAugmenter(probability=0.9, rotation_range=20, seed=None)
    images_augmented.append(aug.fit_transform(viral_pneumonia_images))

images_balanced = np.concatenate(images_augmented, axis=0)
```

---

### `ImageRandomCropper`

Découpe aléatoire ou stratégique d'images.

#### Paramètres

```python
ImageRandomCropper(
    crop_size=(224, 224),      # Taille du crop (height, width)
    mode='random',             # 'random', 'center', ou 'corners'
    padding=0,                 # Padding avant crop (int ou tuple)
    pad_mode='constant',       # 'constant', 'edge', 'reflect', 'wrap'
    seed=None,
    verbose=True
)
```

#### Modes de cropping

| Mode | Description |
|------|-------------|
| **random** | Position aléatoire à chaque image |
| **center** | Toujours au centre |
| **corners** | 5 crops (4 coins + centre) |

#### Exemple d'utilisation

```python
# Crop aléatoire
cropper = ImageRandomCropper(crop_size=(200, 200), mode='random', seed=42)
images_cropped = cropper.fit_transform(images)

# Crop central (déterministe)
cropper_center = ImageRandomCropper(crop_size=(224, 224), mode='center')
images_center = cropper_center.fit_transform(images)

# Multi-crop pour test-time augmentation
cropper_corners = ImageRandomCropper(crop_size=(200, 200), mode='corners')
images_multicrop = cropper_corners.fit_transform(images)
```

---

## 4. Image Features

### `ImageHistogram`

Extrait les histogrammes de distribution des pixels.

#### Paramètres

```python
ImageHistogram(
    bins=32,                    # Nombre de bins
    hist_range=None,            # (min, max) ou None pour auto
    density=False,              # Normaliser l'histogramme
    per_channel=False,          # Histogramme par canal (pour RGB)
    verbose=True
)
```

#### Exemple d'utilisation

```python
# Histogramme simple (32 bins)
hist_extractor = ImageHistogram(bins=32)
features_hist = hist_extractor.fit_transform(images)

print(f"Shape des features: {features_hist.shape}")  # (n_samples, 32)
print(f"Plage utilisée: {hist_extractor.range_}")

# Histogramme haute résolution
hist_hires = ImageHistogram(bins=256, density=True)
features_hires = hist_hires.fit_transform(images)

# Utilisation avec un classifieur
from sklearn.ensemble import RandomForestClassifier

clf = RandomForestClassifier(n_estimators=100)
clf.fit(features_hist, labels)
```

---

### `ImagePCA`

Réduction de dimensionnalité par Analyse en Composantes Principales.

#### Paramètres

```python
ImagePCA(
    n_components=50,           # Nombre de composantes principales
    whiten=False,              # Blanchiment des composantes
    svd_solver='auto',         # 'auto', 'full', 'arpack', 'randomized'
    random_state=None,
    verbose=True
)
```

#### Exemple d'utilisation

```python
# PCA sur images aplaties
pca = ImagePCA(n_components=100, random_state=42)
pca.fit(images_train)

features_pca = pca.transform(images_train)
features_test_pca = pca.transform(images_test)

print(f"Variance expliquée: {pca.explained_variance_ratio_:.2%}")
print(f"Nombre de composantes: {pca.n_components_}")

# Reconstruction d'images
images_reconstructed = pca.inverse_transform(features_pca)

# Visualiser la variance expliquée
import matplotlib.pyplot as plt

plt.plot(np.cumsum(pca.pca_.explained_variance_ratio_))
plt.xlabel('Nombre de composantes')
plt.ylabel('Variance expliquée cumulée')
plt.grid()
plt.show()
```

---

### `ImageStandardScaler`

Standardisation z-score des images.

#### Paramètres

```python
ImageStandardScaler(
    with_mean=True,            # Centrer les données
    with_std=True,             # Réduire par l'écart-type
    reshape_output=True,       # Conserver la forme d'image
    verbose=True
)
```

#### Exemple d'utilisation

```python
# Standardisation classique
scaler = ImageStandardScaler()
scaler.fit(images_train)

images_scaled = scaler.transform(images_train)
images_test_scaled = scaler.transform(images_test)

print(f"Moyenne après scaling: {images_scaled.mean():.4f}")  # ~0.0
print(f"Écart-type après scaling: {images_scaled.std():.4f}")  # ~1.0

# Sans reshape (sortie aplatie)
scaler_flat = ImageStandardScaler(reshape_output=False)
features_flat = scaler_flat.fit_transform(images)
print(f"Shape: {features_flat.shape}")  # (n_samples, height × width)

# Reconstruction
images_original = scaler.inverse_transform(images_scaled)
```

---

## 5. Utilities

### `VisualizeTransformer`

Visualise des échantillons d'images à chaque étape du pipeline.

#### Paramètres

```python
VisualizeTransformer(
    n_samples=5,          # Nombre d'images à afficher
    prefix="step",        # Préfixe pour les titres
    save_dir=None         # Répertoire de sauvegarde (None = pas de save)
)
```

#### Exemple d'utilisation

```python
# Dans un pipeline
from sklearn.pipeline import Pipeline

pipeline = Pipeline([
    ('resize', ImageResizer(img_size=(256, 256))),
    ('viz_resize', VisualizeTransformer(n_samples=3, prefix="after_resize")),
    ('normalize', ImageNormalizer(method='minmax')),
    ('viz_norm', VisualizeTransformer(n_samples=3, prefix="after_normalize")),
])

result = pipeline.fit_transform(images)

# Avec sauvegarde
viz = VisualizeTransformer(
    n_samples=10,
    prefix="augmented",
    save_dir="outputs/visualizations"
)
viz.transform(images_augmented)
```

---

### `SaveTransformer`

Sauvegarde les features extraites sur disque.

#### Paramètres

```python
SaveTransformer(
    save_dir="outputs",
    prefix="features"
)
```

#### Exemple d'utilisation

```python
# Pipeline avec sauvegarde
pipeline = Pipeline([
    ('histogram', ImageHistogram(bins=64)),
    ('save', SaveTransformer(save_dir="outputs/features", prefix="hist_64")),
])

features = pipeline.fit_transform(images)
# Fichier sauvegardé : outputs/features/hist_64.npy

# Rechargement
loaded_features = np.load("outputs/features/hist_64.npy")
```

---

## Pipelines Complets

### Pipeline 1 : Classification Simple

```python
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier

# Pipeline complet : chargement → preprocessing → features → classification
pipeline_simple = Pipeline([
    ('resize', ImageResizer(img_size=(128, 128))),
    ('normalize', ImageNormalizer(method='minmax')),
    ('flatten', ImageFlattener()),
    ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
])

# Entraînement
pipeline_simple.fit(images_train, labels_train)

# Prédiction
predictions = pipeline_simple.predict(images_test)
```

---

### Pipeline 2 : Avec Augmentation et Feature Engineering

```python
# Pour l'entraînement uniquement
pipeline_train = Pipeline([
    ('resize', ImageResizer(img_size=(224, 224))),
    ('augment', ImageAugmenter(
        flip_horizontal=True,
        rotation_range=15,
        brightness_range=(0.9, 1.1),
        probability=0.7,
        seed=42
    )),
    ('normalize', ImageNormalizer(method='standard', per_image=False)),
    ('histogram', ImageHistogram(bins=64)),
])

# Extraction de features
X_train_features = pipeline_train.fit_transform(images_train)

# Pipeline test (sans augmentation)
pipeline_test = Pipeline([
    ('resize', ImageResizer(img_size=(224, 224))),
    ('normalize', ImageNormalizer(method='standard', per_image=False)),
    ('histogram', ImageHistogram(bins=64)),
])

pipeline_test[1] = pipeline_train[2]  # Réutilise le normalizer fitté
pipeline_test[2] = pipeline_train[3]  # Réutilise l'histogram

X_test_features = pipeline_test.transform(images_test)
```

---

### Pipeline 3 : Utilisation des Masques

```python
# Pipeline avec masques pour isoler les poumons
pipeline_masked = Pipeline([
    ('resize', ImageResizer(img_size=(256, 256))),
    ('mask', ImageMasker(mask_paths=mask_paths_train)),
    ('normalize', ImageNormalizer(method='minmax')),
    ('pca', ImagePCA(n_components=100)),
])

X_masked = pipeline_masked.fit_transform(images_train)
```

---

### Pipeline 4 : Équilibrage de Classes

```python
import numpy as np
from collections import Counter

def balance_dataset_with_augmentation(images, labels, target_samples=6000):
    """Équilibre les classes par augmentation."""
    class_counts = Counter(labels)
    
    images_balanced = []
    labels_balanced = []
    
    for class_id, count in class_counts.items():
        # Images de cette classe
        class_mask = labels == class_id
        class_images = images[class_mask]
        
        # Calculer le nombre de répétitions nécessaires
        n_repeats = max(1, target_samples // count)
        
        # Créer un augmenteur pour cette classe
        augmenter = ImageAugmenter(
            flip_horizontal=True,
            rotation_range=20,
            brightness_range=(0.85, 1.15),
            probability=0.8,
            seed=None  # Différent à chaque répétition
        )
        
        # Augmenter
        for _ in range(n_repeats):
            aug_images = augmenter.fit_transform(class_images)
            images_balanced.append(aug_images)
            labels_balanced.extend([class_id] * len(aug_images))
    
    return np.concatenate(images_balanced), np.array(labels_balanced)

# Utilisation
images_balanced, labels_balanced = balance_dataset_with_augmentation(
    images_train, 
    labels_train,
    target_samples=6000
)

print(f"Distribution équilibrée: {Counter(labels_balanced)}")
```

---

## Exemples Pratiques

### Exemple 1 : Chargement du Dataset COVID-19

```python
from pathlib import Path
import numpy as np

# Configuration des chemins
data_root = Path("data/raw/COVID-19_Radiography_Dataset/COVID-19_Radiography_Dataset")

# Classes disponibles
classes = ["COVID", "Lung_Opacity", "Normal", "Viral Pneumonia"]

# Chargement de toutes les images
all_images = []
all_labels = []
all_masks = []

for class_id, class_name in enumerate(classes):
    # Chemins des images
    images_dir = data_root / class_name / "images"
    masks_dir = data_root / class_name / "masks"
    
    image_files = sorted(images_dir.glob("*.png"))
    mask_files = sorted(masks_dir.glob("*.png"))
    
    # Chargement avec ImageLoader
    loader = ImageLoader(verbose=True)
    images = loader.transform([str(f) for f in image_files])
    
    # Stockage
    all_images.extend(images)
    all_labels.extend([class_id] * len(images))
    all_masks.extend([str(f) for f in mask_files])
    
    print(f"{class_name}: {len(images)} images chargées")

# Conversion en arrays
all_images = np.array(all_images)
all_labels = np.array(all_labels)

print(f"\nDataset complet: {len(all_images)} images")
print(f"Distribution: {Counter(all_labels)}")
```

---

### Exemple 2 : Pipeline de Preprocessing Complet

```python
from sklearn.model_selection import train_test_split

# Split train/test stratifié
X_train, X_test, y_train, y_test, masks_train, masks_test = train_test_split(
    all_images, all_labels, all_masks,
    test_size=0.2,
    stratify=all_labels,
    random_state=42
)

# Pipeline de preprocessing
preprocess_pipeline = Pipeline([
    ('resize', ImageResizer(img_size=(224, 224))),
    ('normalize', ImageNormalizer(method='minmax', per_image=False)),
    ('viz', VisualizeTransformer(n_samples=5, prefix="preprocessed")),
])

# Application
X_train_prep = preprocess_pipeline.fit_transform(X_train)
X_test_prep = preprocess_pipeline.transform(X_test)

print(f"Train shape: {X_train_prep.shape}")
print(f"Test shape: {X_test_prep.shape}")
```

---

### Exemple 3 : Augmentation Ciblée pour Classes Minoritaires

```python
# Identifier la classe minoritaire
class_counts = Counter(y_train)
minority_class = min(class_counts, key=class_counts.get)
majority_count = max(class_counts.values())

print(f"Classe minoritaire: {classes[minority_class]}")
print(f"Nombre d'images: {class_counts[minority_class]}")

# Extraire les images de la classe minoritaire
minority_mask = y_train == minority_class
X_minority = X_train_prep[minority_mask]

# Calculer le nombre d'augmentations nécessaires
n_augmentations_needed = majority_count - class_counts[minority_class]
n_repeats = (n_augmentations_needed // class_counts[minority_class]) + 1

# Augmenter
augmenter = ImageAugmenter(
    flip_horizontal=True,
    rotation_range=25,
    brightness_range=(0.8, 1.2),
    noise_std=0.01,
    probability=0.9,
    seed=42
)

X_augmented = []
for i in range(n_repeats):
    X_aug = augmenter.fit_transform(X_minority)
    X_augmented.append(X_aug)

X_augmented = np.concatenate(X_augmented)[:n_augmentations_needed]
y_augmented = np.full(len(X_augmented), minority_class)

# Combiner avec le dataset original
X_train_balanced = np.concatenate([X_train_prep, X_augmented])
y_train_balanced = np.concatenate([y_train, y_augmented])

print(f"Dataset équilibré: {Counter(y_train_balanced)}")
```

---

### Exemple 4 : Extraction de Features Multi-Niveaux

```python
# Feature engineering avec plusieurs extracteurs
from sklearn.pipeline import FeatureUnion

# Créer plusieurs extracteurs de features
feature_union = FeatureUnion([
    ('histogram', ImageHistogram(bins=64)),
    ('pca', ImagePCA(n_components=50)),
])

# Pipeline complet
pipeline_features = Pipeline([
    ('resize', ImageResizer(img_size=(128, 128))),
    ('normalize', ImageNormalizer(method='standard')),
    ('features', feature_union),
])

# Extraction
X_train_features = pipeline_features.fit_transform(X_train)
X_test_features = pipeline_features.transform(X_test)

print(f"Features extraites: {X_train_features.shape}")
# Shape: (n_samples, 64 + 50) = (n_samples, 114)
```

---

### Exemple 5 : Pipeline avec Masques et Visualisation

```python
# Pipeline complet avec masques
config_masker = MaskerConfig(mask_threshold=0.5, resize_masks=True)

pipeline_with_masks = Pipeline([
    ('resize', ImageResizer(img_size=(256, 256))),
    ('viz_original', VisualizeTransformer(n_samples=3, prefix="1_original")),
    ('mask', ImageMasker(mask_paths=masks_train, config=config_masker)),
    ('viz_masked', VisualizeTransformer(n_samples=3, prefix="2_masked")),
    ('normalize', ImageNormalizer(method='minmax')),
    ('viz_normalized', VisualizeTransformer(n_samples=3, prefix="3_normalized")),
    ('flatten', ImageFlattener()),
])

# Exécution
X_processed = pipeline_with_masks.fit_transform(X_train)
```

---

## Bonnes Pratiques

### 1. Gestion de la Mémoire

```python
# ❌ Mauvais : charge tout en mémoire
all_images = ImageLoader().transform(all_paths)  # Peut saturer la RAM

# ✅ Bon : traitement par batch
batch_size = 100
for i in range(0, len(all_paths), batch_size):
    batch_paths = all_paths[i:i+batch_size]
    batch_images = loader.transform(batch_paths)
    # Traiter le batch
```

### 2. Stratification du Split

```python
# ✅ Toujours stratifier pour dataset déséquilibré
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    stratify=y,  # ← Important !
    random_state=42
)
```

### 3. Normalisation Cohérente

```python
# ✅ Fitter sur train, transformer sur test
normalizer = ImageNormalizer(method='minmax')
normalizer.fit(X_train)  # Calcule min/max sur train uniquement

X_train_norm = normalizer.transform(X_train)
X_test_norm = normalizer.transform(X_test)  # Utilise les stats de train
```

### 4. Augmentation Uniquement sur Train

```python
# ✅ Augmentation sur train, pas sur test
augmenter = ImageAugmenter(probability=0.7)
X_train_aug = augmenter.fit_transform(X_train)

# Test sans augmentation
X_test_processed = preprocessor.transform(X_test)
```

### 5. Reproductibilité

```python
# ✅ Fixer les seeds pour reproductibilité
augmenter = ImageAugmenter(seed=42)
cropper = ImageRandomCropper(seed=42)
pca = ImagePCA(random_state=42)
```

### 6. Validation des Dimensions

```python
# ✅ Vérifier les shapes à chaque étape
print(f"Shape après resize: {images_resized.shape}")
print(f"Shape après flatten: {images_flat.shape}")
assert images_flat.shape[0] == len(labels), "Mismatch samples/labels"
```

### 7. Gestion des Erreurs

```python
# ✅ Utiliser fail_on_error=False pour robustesse
loader = ImageLoader(fail_on_error=False, verbose=True)
images = loader.transform(paths)

# Vérifier les échecs
if loader.failed_images_:
    print(f"Images échouées: {loader.failed_images_}")
    # Nettoyer les labels correspondants
```

---

## Troubleshooting

### Problème 1 : `ValueError: No valid images could be loaded`

**Cause** : Tous les chemins sont invalides ou les images sont corrompues

**Solution** :
```python
# Vérifier les chemins
for path in image_paths[:5]:
    print(f"{path}: {Path(path).exists()}")

# Utiliser validate_paths=True
loader = ImageLoader(validate_paths=True, fail_on_error=False)
```

---

### Problème 2 : `ValueError: Number of masks must match number of images`

**Cause** : Désynchronisation entre images et masques

**Solution** :
```python
# Vérifier l'alignement
assert len(image_paths) == len(mask_paths), "Mismatch count"

# Trier pour garantir l'ordre
image_paths = sorted(image_paths)
mask_paths = sorted(mask_paths)
```

---

### Problème 3 : Memory Error avec des datasets volumineux

**Cause** : Trop d'images chargées simultanément

**Solution** :
```python
# Traitement par batch avec générateurs
def batch_generator(paths, batch_size=100):
    for i in range(0, len(paths), batch_size):
        yield loader.transform(paths[i:i+batch_size])

for batch in batch_generator(all_paths):
    # Traiter le batch
    process(batch)
```

---

### Problème 4 : Shape mismatch après augmentation

**Cause** : Les transformations changent les dimensions

**Solution** :
```python
# Vérifier la shape avant/après
print(f"Shape avant: {images.shape}")
images_aug = augmenter.fit_transform(images)
print(f"Shape après: {images_aug.shape}")

# Redimensionner si nécessaire
if images_aug.shape != images.shape:
    resizer = ImageResizer(img_size=images.shape[1:3])
    images_aug = resizer.fit_transform(images_aug)
```

---

### Problème 5 : `RuntimeError: Transformer must be fitted`

**Cause** : Appel de `transform()` sans `fit()` préalable

**Solution** :
```python
# ❌ Mauvais
normalizer = ImageNormalizer()
X_norm = normalizer.transform(X)  # Erreur !

# ✅ Bon
normalizer = ImageNormalizer()
normalizer.fit(X_train)
X_norm = normalizer.transform(X_train)

# Ou
X_norm = normalizer.fit_transform(X_train)
```

---

### Problème 6 : Augmentation ne modifie pas les images

**Cause** : Probabilité trop basse ou seed identique

**Solution** :
```python
# Vérifier la probabilité
augmenter = ImageAugmenter(probability=0.9)  # Augmente la proba

# Vérifier l'attribut
images_aug = augmenter.fit_transform(images)
print(f"Images modifiées: {augmenter.n_images_augmented_}")

# Utiliser seed=None pour variation
augmenter = ImageAugmenter(seed=None)
```

---

## Références

- **Dataset COVID-19** : Voir `data/DATASET_DOCUMENTATION.md`
- **Configuration des pipelines** : `src/features/Pipelines/Configs_Pipelines/`
- **Code source** : `src/features/Pipelines/transformateurs/`

---

## Support

Pour toute question ou problème :
1. Vérifier ce guide
2. Consulter les docstrings des transformateurs
3. Vérifier les logs avec `verbose=True`
4. Tester avec un petit échantillon d'abord

---

**Dernière mise à jour** : 10 décembre 2025
