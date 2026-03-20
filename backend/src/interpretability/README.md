# 🔍 Modules d'Interprétabilité pour Deep Learning

Modules complets pour comprendre les décisions des modèles CNN appliqués à la classification COVID-19.

## 📦 Installation

```bash
pip install lime shap scikit-image
```

## 🎯 Modules Disponibles

### 1. **GradCAM** (`gradcam.py`)
Visualise les zones d'attention du modèle via les gradients des couches convolutionnelles.

**Classes:**
- `GradCAM`: Calcul des heatmaps Grad-CAM
- `visualize_gradcam()`: Visualisation simple
- `visualize_gradcam_grid()`: Grille de visualisations
- `compare_layers()`: Comparaison entre couches
- `overlay_heatmap()`: Superposition heatmap/image

**Exemple:**
```python
from src.interpretability import GradCAM, visualize_gradcam

# Créer l'explainer
gradcam = GradCAM(model, layer_name='block5_conv3')

# Calculer la heatmap
heatmap = gradcam.compute_heatmap(image, class_idx=0)

# Visualiser
visualize_gradcam(image, heatmap, class_name='COVID', confidence=0.95)
```

### 2. **LIME** (`lime_explainer.py`)
Explications par segmentation d'image (super-pixels).

**Classes:**
- `LIMEImageExplainer`: Explainer LIME pour images
- `quick_lime_explanation()`: Fonction rapide

**Méthodes de segmentation:**
- `quickshift`: Rapide, bon équilibre
- `felzenszwalb`: Segmentation basée sur les graphes
- `slic`: Simple Linear Iterative Clustering

**Exemple:**
```python
from src.interpretability import LIMEImageExplainer

# Créer l'explainer
explainer = LIMEImageExplainer(model.predict, num_samples=1000)

# Générer l'explication
explanation = explainer.explain_instance(image, top_labels=1, num_features=10)

# Visualiser
explainer.visualize_explanation(image, explanation, label=0, num_features=5)
```

### 3. **SHAP** (`shap_explainer.py`)
Valeurs de Shapley pour explications au niveau pixel.

**Classes:**
- `SHAPExplainer`: DeepExplainer pour TensorFlow/Keras
- `quick_shap_explanation()`: Fonction rapide

**Visualisations:**
- Image plot (magnitude + signed)
- Heatmap overlay
- Summary plot
- Decision plot
- Comparaison entre classes

**Exemple:**
```python
from src.interpretability import SHAPExplainer

# Créer l'explainer (nécessite background data)
explainer = SHAPExplainer(model, background_data)

# Calculer les valeurs SHAP
shap_values = explainer.explain(images)

# Visualiser
explainer.visualize_image_plot(image, shap_values[0], class_idx=0)
```

### 4. **Utilitaires** (`utils.py`)
Fonctions communes pour comparer et analyser les explications.

**Fonctions principales:**
- `plot_multiple_explanations()`: Compare les 3 méthodes
- `create_interpretation_report()`: Rapport complet
- `batch_explain()`: Explications en batch
- `compute_explanation_metrics()`: Métriques d'évaluation
- `save_explanation()` / `load_explanation()`: Sauvegarde/Chargement

**Exemple:**
```python
from src.interpretability import plot_multiple_explanations

# Comparer les 3 méthodes côte à côte
fig = plot_multiple_explanations(
    image,
    gradcam_heatmap=heatmap,
    lime_explanation=lime_exp,
    shap_values=shap_vals,
    class_idx=0,
    class_name='COVID',
    confidence=0.95
)
```

## 🚀 Usage Rapide

### Option 1: Grad-CAM (Recommandé pour la rapidité)

```python
from src.interpretability import GradCAM, visualize_gradcam

gradcam = GradCAM(model)
heatmap = gradcam.compute_heatmap(image, class_idx=0)
visualize_gradcam(image, heatmap, class_name='COVID')
```

### Option 2: LIME (Bon équilibre)

```python
from src.interpretability import LIMEImageExplainer

explainer = LIMEImageExplainer(model.predict)
explanation = explainer.explain_instance(image, top_labels=1)
explainer.visualize_explanation(image, explanation, label=0)
```

### Option 3: SHAP (Le plus rigoureux)

```python
from src.interpretability import SHAPExplainer

explainer = SHAPExplainer(model, background_data)
shap_values = explainer.explain(image[np.newaxis, ...])
explainer.visualize_image_plot(image, shap_values[0], class_idx=0)
```

### Option 4: Rapport Complet

```python
from src.interpretability import create_interpretation_report

report = create_interpretation_report(
    image,
    model,
    class_names=['COVID', 'Normal', 'Lung_Opacity', 'Viral Pneumonia'],
    true_label=0,
    pred_label=0,
    confidence=0.95,
    save_dir=Path('./results'),
    background_data=X_train[:100]  # Pour SHAP
)
```

## 📊 Comparaison des Méthodes

| Critère | Grad-CAM | LIME | SHAP |
|---------|----------|------|------|
| **Vitesse** | ⚡⚡⚡ Très rapide | ⚡⚡ Moyen | ⚡ Lent |
| **Précision** | ⭐⭐⭐ Bonne | ⭐⭐ Moyenne | ⭐⭐⭐ Excellente |
| **Interprétabilité** | ⭐⭐⭐ Intuitive | ⭐⭐⭐ Très bonne | ⭐⭐ Complexe |
| **Model-agnostic** | ❌ CNN uniquement | ✅ Oui | ✅ Oui |
| **Background data** | ❌ Non requis | ❌ Non requis | ✅ Requis |
| **Batch processing** | ✅ Excellent | ⚠️ Possible | ⚠️ Lent |

## 💡 Recommandations d'Usage

### Pour la Production
- **Grad-CAM**: Rapide, efficace, suffisant pour la majorité des cas

### Pour l'Analyse Exploratoire
- **Grad-CAM + LIME**: Combiner vision globale et locale

### Pour la Recherche
- **SHAP**: Explications théoriquement fondées

### Pour Communication Médicale
- **Grad-CAM**: Plus visuel et facile à comprendre

## 🔧 Configuration Avancée

### Grad-CAM - Choix de la couche

```python
# Lister les couches disponibles
gradcam = GradCAM(model)
layers = gradcam.get_available_layers()
print(layers)

# Utiliser une couche spécifique
gradcam = GradCAM(model, layer_name='block4_conv3')
```

### LIME - Méthodes de segmentation

```python
# Comparer les méthodes
explainer.compare_segmentation_methods(
    image,
    methods=['quickshift', 'felzenszwalb', 'slic']
)

# Choisir la meilleure pour vos données
explainer = LIMEImageExplainer(
    model.predict,
    segmentation_method='slic',  # Meilleure segmentation
    num_samples=2000  # Plus d'échantillons = meilleure précision
)
```

### SHAP - Optimisation

```python
# Utiliser moins de background data pour accélérer
background_subset = X_train[:50]  # 50 images suffisent souvent

# Désactiver la vérification d'additivité (plus rapide)
shap_values = explainer.explain(images, check_additivity=False)
```

## 📈 Métriques d'Évaluation

Évaluez la qualité des explications:

```python
from src.interpretability.utils import (
    compute_explanation_metrics,
    visualize_metrics_comparison
)

# Calculer les métriques
metrics = compare_explanation_metrics(
    gradcam_heatmap=heatmap,
    lime_mask=mask,
    shap_heatmap=shap_map,
    image=image
)

# Métriques disponibles:
# - coverage: Pourcentage de l'image couvert
# - mean_intensity: Intensité moyenne
# - max_intensity: Intensité maximale
# - concentration: Degré de concentration (entropie inverse)
```

## 📚 Références

- **Grad-CAM**: [Selvaraju et al., 2017](https://arxiv.org/abs/1610.02391)
- **LIME**: [Ribeiro et al., 2016](https://arxiv.org/abs/1602.04938)
- **SHAP**: [Lundberg & Lee, 2017](https://arxiv.org/abs/1705.07874)

## 🐛 Troubleshooting

### Erreur: "LIME non installé"
```bash
pip install lime
```

### Erreur: "SHAP non installé"
```bash
pip install shap
```

### SHAP trop lent
- Réduire le nombre d'images background (50 suffit)
- Désactiver `check_additivity=False`
- Utiliser Grad-CAM à la place

### Grad-CAM: Couche non trouvée
```python
# Lister les couches disponibles
gradcam = GradCAM(model)
print(gradcam.get_available_layers())
```

## 📖 Documentation Complète

Voir le notebook de démonstration: `notebooks/interpretability_demo.ipynb`

## ✅ Tests

```python
# Test rapide
from src.interpretability import GradCAM

model = keras.models.load_model('models/vgg16_finetuned_best.keras')
gradcam = GradCAM(model)
print("✅ Modules d'interprétabilité opérationnels")
```

## 🎯 Prochaines Étapes

1. Intégrer dans le pipeline de production
2. Créer des dashboards interactifs (Streamlit/Dash)
3. Automatiser l'analyse des erreurs
4. Générer des rapports PDF pour les médecins
