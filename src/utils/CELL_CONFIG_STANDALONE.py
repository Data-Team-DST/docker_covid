"""
╔════════════════════════════════════════════════════════════════════════════╗
║  🎯 CELLULE DE CONFIGURATION STANDALONE - COPIER-COLLER DANS VOS NOTEBOOKS ║
╚════════════════════════════════════════════════════════════════════════════╝

INSTRUCTIONS:
-------------
1. Copiez TOUT le contenu de cette cellule
2. Collez-le comme PREMIÈRE CELLULE de votre notebook
3. Exécutez la cellule
4. Les variables sont prêtes à l'emploi !

Cette cellule est 100% autonome et fonctionne partout :
✅ Google Colab (clone repo + mount Drive automatiquement)
✅ Jupyter Local (notebook en local)

APRÈS EXÉCUTION, VOUS POUVEZ UTILISER:
- project_root, data_dir, categories: Chemins et configuration
- ENV: Environnement détecté ('colab' ou 'local')
- Tous les transformateurs importés et prêts à l'emploi

"""

# =============================================================================
# IMPORTS STANDARDS
# =============================================================================

import os
import sys
import subprocess
from pathlib import Path


# =============================================================================
# DÉTECTION AUTOMATIQUE DE L'ENVIRONNEMENT
# =============================================================================

def detect_environment():
    """Détecte l'environnement : colab ou local"""
    try:
        import google.colab
        return "colab"
    except ImportError:
        return "local"

ENV = detect_environment()
print(f"🌍 Environnement: {ENV.upper()}")


# =============================================================================
# BOOTSTRAP COLAB (Clone + Install si nécessaire)
# =============================================================================

if ENV == "colab":
    print("\n🚀 Bootstrap Colab...")
    
    os.chdir('/content')
    if not os.path.exists('/content/DS_COVID_ORGA'):
        print("📥 Clonage du repository...")
        subprocess.run(['git', 'clone', 'https://github.com/Data-Team-DST/DS_COVID.git', 'DS_COVID_ORGA'], check=True)
    
    os.chdir('/content/DS_COVID_ORGA')
    
    # Checkout de la branche rafael2
    result = subprocess.run(
        ['git', 'checkout', '-b', 'rafael2', 'origin/rafael2'],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        # Si la branche locale existe déjà, juste switcher
        subprocess.run(['git', 'checkout', 'rafael2'], capture_output=True)
    
    # ✅ Colab a déjà tous les packages nécessaires
    print("✅ Utilisation des packages Colab natifs")
    
    # Montage Google Drive pour le dataset
    print("\n💾 Montage Google Drive...")
    from google.colab import drive
    drive.mount('/content/drive', force_remount=False)
    
    # Vérifier le dataset sur Drive
    drive_dataset = Path('/content/drive/MyDrive/DS_COVID/archive_covid.zip')
    local_dataset = Path('./data/raw/COVID-19_Radiography_Dataset/COVID-19_Radiography_Dataset')
    
    if local_dataset.exists():
        print("✅ Dataset déjà extrait localement")
    elif drive_dataset.exists():
        print("📦 Extraction dataset depuis Drive...")
        os.makedirs('./data/raw/COVID-19_Radiography_Dataset/', exist_ok=True)
        subprocess.run(['unzip', '-o', '-q', str(drive_dataset), '-d', './data/raw/COVID-19_Radiography_Dataset/'], check=True)
        print("✅ Dataset extrait")
    else:
        print(f"⚠️ Dataset non trouvé sur Drive: {drive_dataset}")
        print("   💡 Téléchargez depuis Kaggle et uploadez sur Drive")
        print("   https://www.kaggle.com/datasets/tawsifurrahman/covid19-radiography-database")
    
    print("\n✅ Bootstrap Colab terminé")


# =============================================================================
# CONFIGURATION DES CHEMINS
# =============================================================================

# Déterminer project_root selon l'environnement
if ENV == "colab":
    project_root = Path('/content/DS_COVID_ORGA')
else:  # local
    # Depuis un notebook dans notebooks/ ou à la racine
    project_root = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()

# Ajouter au sys.path pour les imports
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    print(f"✅ Chemin projet ajouté: {project_root}")

# Configuration manuelle (pas de fichier config.py dans ce projet)
DATA_DIR = project_root / 'data' / 'raw' / 'COVID-19_Radiography_Dataset' / 'COVID-19_Radiography_Dataset'
CATEGORIES = ['COVID', 'Lung_Opacity', 'Normal', 'Viral Pneumonia']
IMG_SIZE = (299, 299) if ENV == "colab" else (128, 128)  # Plus grand en colab
BATCH_SIZE = 128 if ENV == "colab" else 32  # Plus grand batch en colab
EPOCHS = 50 if ENV == "colab" else 10  # Moins d'époques en local pour tests rapides
MAX_SAMPLES_PER_CLASS = None if ENV == "colab" else 100 # Pour tests rapides, None pour tout utiliser

print(f"📂 Dataset configuré: {DATA_DIR}")
print(f"🏷️ Classes: {', '.join(CATEGORIES)}")


# =============================================================================
# IMPORTS DES TRANSFORMERS
# =============================================================================

try:
    from src.features.Pipelines.transformateurs.image_loaders import ImageLoader
    from src.features.Pipelines.transformateurs.image_preprocessing import (
        ImageResizer, ImageNormalizer, ImageFlattener, ImageMasker, ImageBinarizer
    )
    from src.features.Pipelines.transformateurs.image_augmentation import (
        ImageAugmenter, ImageRandomCropper
    )
    from src.features.Pipelines.transformateurs.image_features import (
        ImageHistogram, ImagePCA, ImageStandardScaler
    )
    from src.features.Pipelines.transformateurs.utilities import (
        VisualizeTransformer, SaveTransformer
    )
    print("✅ Tous les transformateurs importés")
except ImportError as e:
    print(f"⚠️ Erreur import transformateurs: {e}")
    print(f"   Vérifiez que le projet est bien dans: {project_root}")


# =============================================================================
# IMPORTS ML/DL
# =============================================================================

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tensorflow import keras
import pandas as pd
from collections import Counter
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# Imports ML pour les métriques et modèles
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, f1_score,
    classification_report, confusion_matrix, precision_score, recall_score
)

# Configuration supplémentaire pour les plots
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# =============================================================================
# CONFIGURATION MATPLOTLIB
# =============================================================================

plt.rcParams['figure.figsize'] = (15, 10)
sns.set_style('whitegrid')

# =============================================================================
# AFFICHAGE DU RÉSUMÉ
# =============================================================================

print("\n" + "=" * 70)
print("✅ CONFIGURATION PRÊTE - DS_COVID Project")
print("=" * 70)
print(f"📂 Projet: {project_root}")
print(f"📊 Dataset: {DATA_DIR}")
print(f"🏷️ Classes: {', '.join(CATEGORIES)}")
print(f"🎛️ Images: {IMG_SIZE}")
print(f"🔧 Batch: {BATCH_SIZE} | Époques: {EPOCHS}")
print(f"📐 Dataset accessible: {'✅' if DATA_DIR.exists() else '❌'}")
if not DATA_DIR.exists():
    print(f"   ⚠️ Le dataset doit être placé dans: {DATA_DIR}")
    if ENV == "colab":
        print(f"   💡 Uploadez archive_covid.zip sur Google Drive ou téléchargez directement")
print("=" * 70)
print("\n💡 Variables disponibles:")
print("   • project_root: Racine du projet (Path)")
print("   • data_dir: Dossier des données (Path)")
print("   • categories: Liste des 4 classes")
print("   • img_size: Taille des images (tuple)")
print("   • batch_size, epochs: Hyperparamètres")
print("   • ENV: Environnement actuel")
print("\n🎯 Transformateurs disponibles:")
print("   • Loaders: ImageLoader")
print("   • Preprocessing: ImageResizer, ImageNormalizer, ImageFlattener, ImageMasker, ImageBinarizer")
print("   • Augmentation: ImageAugmenter, ImageRandomCropper")
print("   • Features: ImageHistogram, ImagePCA, ImageStandardScaler")
print("   • Utilities: VisualizeTransformer, SaveTransformer")
print("=" * 70)
