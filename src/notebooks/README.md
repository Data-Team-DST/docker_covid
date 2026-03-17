# 📚 Notebook Utilities - Guide d'Utilisation

Ce module fournit des fonctions réutilisables pour simplifier les notebooks Jupyter.

## 📁 Structure

```
src/notebooks/
├── __init__.py           # Exports des fonctions
└── notebook_utils.py     # Implémentation des fonctions
```

---

## 🚀 Installation

Les fonctions sont automatiquement disponibles après installation du package :

```bash
pip install -e .
```

---

## 📖 Utilisation

### **Import simple**

```python
from src.notebooks import (
    load_dataset,
    create_preprocessing_pipeline,
    build_custom_cnn,
    train_model,
    evaluate_model,
    plot_training_curves,
    run_gradcam_analysis
)
```

---

## 🔧 Fonctions Disponibles

### **1. Data Loading & Preprocessing**

#### `load_dataset()`
Charge les chemins des images et labels depuis le dataset.

```python
image_paths, mask_paths, labels, labels_int = load_dataset(
    data_dir=Path('/path/to/data'),
    categories=['COVID', 'Normal', 'Lung_Opacity', 'Viral Pneumonia'],
    n_images_per_class=None,  # None = toutes les images
    load_masks=False,           # True pour charger les masques
    verbose=True
)
```

**Returns:**
- `image_paths`: Liste des chemins d'images
- `mask_paths`: Liste des chemins de masques (vide si `load_masks=False`)
- `labels`: Liste des labels (strings)
- `labels_int`: Array numpy des labels (integers)

---

#### `create_preprocessing_pipeline()`
Crée une pipeline sklearn pour le preprocessing.

```python
pipeline = create_preprocessing_pipeline(
    img_size=(128, 128),
    color_mode='RGB',        # 'RGB' ou 'L' (grayscale)
    mask_paths=None,         # Optionnel: chemins des masques
    verbose=True
)

# Utiliser la pipeline
images = pipeline.fit_transform(image_paths)
images = images.astype('float32') / 255.0
```

**Étapes de la pipeline:**
1. `ImageLoader` - Charge les images
2. `ImageResizer` - Redimensionne à `img_size`
3. `ImageMasker` - Applique les masques (si `mask_paths` fourni)

---

#### `prepare_train_val_test_split()`
Split les données en train/val/test avec one-hot encoding.

```python
X_train, X_val, X_test, y_train_cat, y_val_cat, y_test_cat = prepare_train_val_test_split(
    images=images,
    labels_int=labels_int,
    num_classes=4,
    test_size=0.15,
    val_size=0.15,
    random_seed=42,
    verbose=True
)
```

**Returns:**
- `X_train`, `X_val`, `X_test`: Images splitées
- `y_train_cat`, `y_val_cat`, `y_test_cat`: Labels one-hot encodés

---

#### `compute_class_weights()`
Calcule les poids de classe pour gérer le déséquilibre.

```python
y_train = np.argmax(y_train_cat, axis=1)  # Convertir one-hot en integer

class_weights = compute_class_weights(
    y_train=y_train,
    categories=['COVID', 'Normal', 'Lung_Opacity', 'Viral Pneumonia'],
    verbose=True
)
```

**Returns:** `{0: 0.95, 1: 1.05, 2: 1.2, 3: 0.8}` - Dict des poids

---

#### `create_data_generators()`
Crée les générateurs Keras avec augmentation optionnelle.

```python
train_gen, val_gen, test_gen = create_data_generators(
    X_train=X_train,
    y_train_cat=y_train_cat,
    X_val=X_val,
    y_val_cat=y_val_cat,
    X_test=X_test,           # Optionnel
    y_test_cat=y_test_cat,   # Optionnel
    batch_size=32,
    augment_train=True,  # Augmentation sur train uniquement
    verbose=True
)
```

**Returns:**
- `train_gen`: Générateur d'entraînement (avec augmentation si `augment_train=True`)
- `val_gen`: Générateur de validation (sans augmentation)
- `test_gen`: Générateur de test (sans augmentation, `None` si X_test non fourni)

**Augmentation appliquée (train uniquement):**
- Rotation: ±10°
- Shift: ±10%
- Zoom: ±10%
- Horizontal flip

---

### **2. Model Building**

#### **2.1. Custom CNN**

#### `build_custom_cnn()`
Construit un CNN custom pour l'imagerie médicale.

```python
model = build_custom_cnn(
    input_shape=(128, 128, 3),
    num_classes=4,
    verbose=True
)
```

**Architecture:**
- 5 blocs convolutionnels: 32 → 64 → 128 → 256 → 512 filtres
- Batch Normalization après chaque Conv2D
- Dropout (0.25-0.5) pour régularisation
- L2 regularization sur couches denses
- ~15M paramètres

---

#### `compile_model()`
Compile le modèle avec métriques standards.

```python
model = compile_model(
    model=model,
    learning_rate=0.001,
    verbose=True
)
```

**Configuration:**
- Optimizer: Adam
- Loss: CategoricalCrossentropy
- Metrics: accuracy, auc, precision, recall

---

#### `create_callbacks()`
Crée les callbacks d'entraînement standards.

```python
callbacks = create_callbacks(
    models_dir=Path('results/models'),
    monitor='val_accuracy',
    patience_early_stop=15,
    patience_reduce_lr=5,
    verbose=True
)
```

**Callbacks inclus:**
1. `EarlyStopping` - Arrête si pas d'amélioration
2. `ReduceLROnPlateau` - Réduit le LR si plateau
3. `ModelCheckpoint` - Sauvegarde le meilleur modèle

---

#### **2.2. Transfer Learning (Fine-Tuning)**

#### `build_transfer_learning_model()`
Construit un modèle de Transfer Learning avec poids ImageNet pré-entraînés.

```python
model, base_model = build_transfer_learning_model(
    base_model_name='InceptionV3',  # 'VGG16', 'ResNet50', 'EfficientNetB0', 'InceptionV3'
    input_shape=(224, 224, 3),
    num_classes=4,
    freeze_base=True,  # True pour feature extraction
    dropout_rate=0.3,
    dense_units=128,
    l2_reg=0.01,
    verbose=True
)
```

**Modèles disponibles:**
- `VGG16` - 138M paramètres
- `ResNet50` - 25M paramètres  
- `EfficientNetB0` - 5M paramètres
- `InceptionV3` - 24M paramètres

**Returns:**
- `model`: Modèle complet (base + head)
- `base_model`: Modèle de base (pour fine-tuning ultérieur)

---

#### `create_transfer_learning_generators()`
Crée des générateurs avec preprocessing spécifique à chaque modèle.

```python
train_gen, val_gen, test_gen = create_transfer_learning_generators(
    X_train=X_train,
    y_train_cat=y_train_cat,
    X_val=X_val,
    y_val_cat=y_val_cat,
    X_test=X_test,           # Optionnel
    y_test_cat=y_test_cat,   # Optionnel
    base_model_name='InceptionV3',
    batch_size=32,
    augment_train=True,
    verbose=True
)
```

**Preprocessing par modèle:**
- `VGG16/ResNet50`: Soustraction mean ImageNet [103.939, 116.779, 123.68]
- `InceptionV3`: Normalisation [-1, 1]
- `EfficientNetB0`: Normalisation [0, 1]

**Augmentation (train uniquement):**
- Rotation: ±10°
- Shift: ±5%
- Zoom: ±5%
- **PAS** de flip horizontal (images médicales)

---

#### `unfreeze_top_layers()`
Dégèle les dernières couches pour le fine-tuning.

```python
model = unfreeze_top_layers(
    base_model=base_model,
    model=model,
    n_layers=4,         # Nombre de couches à dégeler
    learning_rate=5e-5,  # LR très faible pour fine-tuning
    verbose=True
)
```

**Usage typique - 2 phases:**

**Phase 1: Feature Extraction**
```python
# 1. Créer le modèle avec base gelée
model, base_model = build_transfer_learning_model(
    base_model_name='InceptionV3',
    freeze_base=True
)

# 2. Compiler et entraîner
model = compile_model(model, learning_rate=0.001)
history_fe = train_model(model, train_gen, val_gen, class_weights, epochs=80)
```

**Phase 2: Fine-Tuning**
```python
# 3. Dégeler les top layers
model = unfreeze_top_layers(
    base_model=base_model,
    model=model,
    n_layers=4,
    learning_rate=5e-5  # 100x plus faible!
)

# 4. Continuer l'entraînement
history_ft = train_model(model, train_gen, val_gen, class_weights, epochs=50)
```

---

### **3. Training & Evaluation**

#### `train_model()`
Entraîne le modèle.

```python
history = train_model(
    model=model,
    train_generator=train_gen,
    val_generator=val_gen,
    class_weights=class_weights,
    epochs=50,
    callbacks=callbacks,
    verbose=True
)
```

**Returns:** `keras.callbacks.History` - Historique d'entraînement

---

#### `evaluate_model()`
Évalue le modèle sur le test set.

```python
y_pred, y_pred_proba = evaluate_model(
    model=model,
    X_test=X_test,
    y_test_cat=y_test_cat,
    y_test=y_test,  # Labels integer
    categories=['COVID', 'Normal', 'Lung_Opacity', 'Viral Pneumonia'],
    verbose=True
)
```

**Affiche:**
- Loss, Accuracy, AUC, Precision, Recall, F1-Score
- Classification report détaillé

**Returns:**
- `y_pred`: Prédictions (labels integer)
- `y_pred_proba`: Probabilités de prédiction

---

### **4. Visualization**

#### `plot_training_curves()`
Trace les courbes d'apprentissage.

```python
fig = plot_training_curves(
    history=history,
    save_path=Path('results/training_curves.png'),
    figsize=(15, 12)
)
plt.show()
```

**Graphiques:**
- Loss (train/val)
- Accuracy (train/val)
- AUC (train/val)
- Precision & Recall (train/val)

---

#### `plot_confusion_matrix()`
Trace la matrice de confusion.

```python
fig = plot_confusion_matrix(
    y_test=y_test,
    y_pred=y_pred,
    categories=['COVID', 'Normal', 'Lung_Opacity', 'Viral Pneumonia'],
    save_path=Path('results/confusion_matrix.png'),
    figsize=(10, 8)
)
plt.show()
```

---

### **5. Interpretability**

#### `select_sample_images()`
Sélectionne des images échantillons pour l'analyse.

```python
sample_indices = select_sample_images(
    X_test=X_test,
    y_test=y_test,
    y_pred=y_pred,
    y_pred_proba=y_pred_proba,
    categories=['COVID', 'Normal', 'Lung_Opacity', 'Viral Pneumonia'],
    n_samples=6,
    random_seed=42,
    verbose=True
)
```

---

#### `run_gradcam_analysis()`
Exécute l'analyse Grad-CAM.

```python
gradcam, heatmaps = run_gradcam_analysis(
    model=model,
    X_test=X_test,
    y_pred=y_pred,
    y_pred_proba=y_pred_proba,
    categories=['COVID', 'Normal', 'Lung_Opacity', 'Viral Pneumonia'],
    sample_indices=sample_indices,
    save_dir=Path('results/interpretability'),
    verbose=True
)
```

**Returns:**
- `gradcam`: Instance de GradCAM
- `heatmaps`: Liste des heatmaps générées

---

## 📝 Exemple Complet

```python
# 1. Imports
from src.notebooks import *
import numpy as np
import matplotlib.pyplot as plt

# 2. Charger les données
image_paths, _, labels, labels_int = load_dataset(
    data_dir=config.data_dir,
    categories=config.classes
)

# 3. Preprocessing
pipeline = create_preprocessing_pipeline(img_size=(128, 128))
images = pipeline.fit_transform(image_paths)
images = images.astype('float32') / 255.0

# 4. Split
X_train, X_val, X_test, y_train_cat, y_val_cat, y_test_cat = prepare_train_val_test_split(
    images, labels_int, num_classes=len(config.classes)
)

y_train = np.argmax(y_train_cat, axis=1)
y_test = np.argmax(y_test_cat, axis=1)

# 5. Class weights et generators
class_weights = compute_class_weights(y_train, config.classes)
train_gen, val_gen, test_gen = create_data_generators(
    X_train, y_train_cat, X_val, y_val_cat, X_test, y_test_cat, batch_size=32
)

# 6. Modèle
model = build_custom_cnn(input_shape=(128, 128, 3), num_classes=4)
model = compile_model(model)
callbacks = create_callbacks(models_dir=Path('results/models'))

# 7. Entraînement
history = train_model(model, train_gen, val_gen, class_weights, epochs=50, callbacks=callbacks)

# 8. Évaluation
y_pred, y_pred_proba = evaluate_model(model, X_test, y_test_cat, y_test, config.classes)

# 9. Visualisation
plot_training_curves(history, save_path=Path('results/curves.png'))
plot_confusion_matrix(y_test, y_pred, config.classes, save_path=Path('results/cm.png'))

# 10. Interprétabilité
samples = select_sample_images(X_test, y_test, y_pred, y_pred_proba, config.classes)
gradcam, heatmaps = run_gradcam_analysis(
    model, X_test, y_pred, y_pred_proba, config.classes, samples, Path('results')
)

plt.show()
```

---

## 📝 Exemple Complet

### **Custom CNN**

```python
# 1. Imports
from src.notebooks import *
import numpy as np
import matplotlib.pyplot as plt

# 2. Charger les données
image_paths, _, labels, labels_int = load_dataset(
    data_dir=config.data_dir,
    categories=config.classes
)

# 3. Preprocessing
pipeline = create_preprocessing_pipeline(img_size=(128, 128))
images = pipeline.fit_transform(image_paths)
images = images.astype('float32') / 255.0

# 4. Split
X_train, X_val, X_test, y_train_cat, y_val_cat, y_test_cat = prepare_train_val_test_split(
    images, labels_int, num_classes=len(config.classes)
)

y_train = np.argmax(y_train_cat, axis=1)
y_test = np.argmax(y_test_cat, axis=1)

# 5. Class weights et generators
class_weights = compute_class_weights(y_train, config.classes)
train_gen, val_gen, test_gen = create_data_generators(
    X_train, y_train_cat, X_val, y_val_cat, X_test, y_test_cat, batch_size=32
)

# 6. Modèle
model = build_custom_cnn(input_shape=(128, 128, 3), num_classes=4)
model = compile_model(model)
callbacks = create_callbacks(models_dir=Path('results/models'))

# 7. Entraînement
history = train_model(model, train_gen, val_gen, class_weights, epochs=50, callbacks=callbacks)

# 8. Évaluation
y_pred, y_pred_proba = evaluate_model(model, X_test, y_test_cat, y_test, config.classes)

# 9. Visualisation
plot_training_curves(history, save_path=Path('results/curves.png'))
plot_confusion_matrix(y_test, y_pred, config.classes, save_path=Path('results/cm.png'))

# 10. Interprétabilité
samples = select_sample_images(X_test, y_test, y_pred, y_pred_proba, config.classes)
gradcam, heatmaps = run_gradcam_analysis(
    model, X_test, y_pred, y_pred_proba, config.classes, samples, Path('results')
)

plt.show()
```

---

### **Transfer Learning (InceptionV3)**

```python
# 1-4. Identique au Custom CNN jusqu'au split

# 5. Class weights
y_train = np.argmax(y_train_cat, axis=1)
class_weights = compute_class_weights(y_train, config.classes)

# 6. Créer le modèle Transfer Learning
model, base_model = build_transfer_learning_model(
    base_model_name='InceptionV3',
    input_shape=(224, 224, 3),  # ⚠️ 224x224 pour Transfer Learning!
    num_classes=4,
    freeze_base=True  # Phase 1: Feature Extraction
)

# 7. Générateurs avec preprocessing InceptionV3
train_gen, val_gen, test_gen = create_transfer_learning_generators(
    X_train, y_train_cat, X_val, y_val_cat, X_test, y_test_cat,
    base_model_name='InceptionV3',
    batch_size=32
)

# 8. Compiler
model = compile_model(model, learning_rate=0.001)
callbacks = create_callbacks(models_dir=Path('results/models_tl'))

# 9. PHASE 1: Feature Extraction (base gelée)
print("🚀 PHASE 1: Feature Extraction")
history_fe = train_model(
    model, train_gen, val_gen, class_weights, 
    epochs=80, callbacks=callbacks
)

# 10. PHASE 2: Fine-Tuning (dégeler top layers)
print("🚀 PHASE 2: Fine-Tuning")
model = unfreeze_top_layers(
    base_model=base_model,
    model=model,
    n_layers=30,  # InceptionV3: dégeler les 30 dernières couches
    learning_rate=5e-5  # LR 100x plus faible!
)

history_ft = train_model(
    model, train_gen, val_gen, class_weights, 
    epochs=50, callbacks=callbacks
)

# 11. Évaluation
y_pred, y_pred_proba = evaluate_model(model, X_test, y_test_cat, y_test, config.classes)

# 12. Visualisation
plot_training_curves(history_ft, save_path=Path('results/curves_ft.png'))
plot_confusion_matrix(y_test, y_pred, config.classes, save_path=Path('results/cm_tl.png'))

plt.show()
```

---

### **Comparaison de Plusieurs Modèles**

```python
# Tester plusieurs architectures Transfer Learning
models_to_test = ['VGG16', 'ResNet50', 'EfficientNetB0', 'InceptionV3']
results = {}

for model_name in models_to_test:
    print(f"\n{'='*70}")
    print(f"ENTRAÎNEMENT: {model_name}")
    print(f"{'='*70}")
    
    # 1. Créer le modèle
    model, base_model = build_transfer_learning_model(
        base_model_name=model_name,
        freeze_base=True
    )
    
    # 2. Générateurs avec preprocessing spécifique
    train_gen, val_gen, test_gen = create_transfer_learning_generators(
        X_train, y_train_cat, X_val, y_val_cat, X_test, y_test_cat,
        base_model_name=model_name
    )
    
    # 3. Feature Extraction
    model = compile_model(model, learning_rate=0.001)
    callbacks = create_callbacks(models_dir=Path(f'results/{model_name.lower()}'))
    
    history_fe = train_model(model, train_gen, val_gen, class_weights, epochs=80, callbacks=callbacks)
    
    # 4. Fine-Tuning
    n_layers = 4 if model_name != 'InceptionV3' else 30
    model = unfreeze_top_layers(base_model, model, n_layers=n_layers, learning_rate=5e-5)
    
    history_ft = train_model(model, train_gen, val_gen, class_weights, epochs=50, callbacks=callbacks)
    
    # 5. Évaluation
    y_pred, y_pred_proba = evaluate_model(model, X_test, y_test_cat, y_test, config.classes)
    
    # Sauvegarder les résultats
    results[model_name] = {
        'y_pred': y_pred,
        'y_pred_proba': y_pred_proba,
        'history_fe': history_fe,
        'history_ft': history_ft
    }

# Comparer les résultats
print("\n" + "="*70)
print("COMPARAISON DES MODÈLES")
print("="*70)

from sklearn.metrics import accuracy_score, precision_score, recall_score

for model_name, res in results.items():
    acc = accuracy_score(y_test, res['y_pred'])
    prec = precision_score(y_test, res['y_pred'], average='weighted')
    rec = recall_score(y_test, res['y_pred'], average='weighted')
    
    print(f"\n{model_name:20s}")
    print(f"  Accuracy:  {acc:.4f}")
    print(f"  Precision: {prec:.4f}")
    print(f"  Recall:    {rec:.4f}")
```

---

## 🎯 Avantages

✅ **Code plus court** : Notebooks réduits de ~60%  
✅ **Réutilisable** : Mêmes fonctions dans tous les notebooks  
✅ **Maintenable** : Modifications centralisées  
✅ **Testé** : Fonctions unitaires testables  
✅ **Documenté** : Docstrings complètes  

---

## 🔄 Migration d'un Ancien Notebook

**Avant** (code répétitif):
```python
# 50+ lignes pour charger les données
image_paths = []
for cat in categories:
    # ...
    
# 30+ lignes pour la pipeline
# ...

# 60+ lignes pour le modèle
# ...
```

**Après** (fonctions réutilisables):
```python
image_paths, _, labels, labels_int = load_dataset(data_dir, categories)
pipeline = create_preprocessing_pipeline(img_size=(128, 128))
images = pipeline.fit_transform(image_paths)
model = build_custom_cnn(input_shape=(128, 128, 3))
```

**Réduction:** ~200 lignes → ~20 lignes ! 🚀

---

## 📚 Documentation Supplémentaire

Consultez les docstrings de chaque fonction pour plus de détails :

```python
help(load_dataset)
help(build_custom_cnn)
help(train_model)
```

---

## 🐛 Debugging

En cas d'erreur, vérifiez :

1. **Imports** : `from src.notebooks import *`
2. **Shapes** : Les dimensions des arrays
3. **Verbose** : Activer `verbose=True` pour diagnostiquer
4. **Logs** : Consulter les messages d'erreur détaillés

---

## 🚀 Prochaines Étapes

- [ ] Ajouter fonctions LIME/SHAP
- [ ] Support Transfer Learning (InceptionV3, ResNet)
- [ ] Export modèles (ONNX, TFLite)
- [ ] Comparaison automatique de modèles

---

**Auteur:** Data Pipeline Team  
**Date:** Novembre 2025  
**Licence:** MIT
