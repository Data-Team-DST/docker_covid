import argparse
from pathlib import Path
from PIL import Image
import numpy as np
import cv2
from tqdm import tqdm


def normalize_image(img_array, method='minmax'):
    """
    Normalise une image selon la méthode choisie.
    
    Args:
        img_array: np.array (H, W) - image grayscale
        method: str - 'minmax' pour [0,1] ou 'standard' pour z-score
    
    Returns:
        np.array normalisée (float32)
    """
        if method == 'minmax':
            # Normalisation min-max vers [0, 1]
            img_norm = (img_array - img_array.min()) / (img_array.max() - img_array.min() + 1e-8)
        elif method == 'standard':
            # Standardisation (z-score)
            img_norm = (img_array - img_array.mean()) / (img_array.std() + 1e-8)
        else:
            raise ValueError("method doit être 'minmax' ou 'standard'")
        
        return img_norm.astype(np.float32)
        

def create_dataset(resolution, with_masking, normalize_method=None):
    # Configuration
    PROJECT_ROOT = Path(__file__).parent
    SOURCE_PATH = PROJECT_ROOT / "data" / "raw" / "COVID-19_Radiography_Dataset"
    color_mode = 'L'  # Mode grayscale imposé pour la radiographie
    if with_masking:
        base_output = f"masked_full_dataset_{resolution}_{resolution}_{color_mode}"
        if normalize_method:
            base_output += f"_{normalize_method}"
        OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / base_output
    else:
        base_output = f"unmasked_full_dataset_{resolution}_{resolution}_{color_mode}"
        if normalize_method:
            base_output += f"_{normalize_method}"
        OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / base_output

    # Paramètres
    TARGET_SIZE = (resolution, resolution)
    CLASSES = ["COVID", "Normal", "Lung_Opacity", "Viral Pneumonia"]

    print(f"Dataset source: {SOURCE_PATH}")
    print(f"Dataset de sortie: {OUTPUT_PATH}")
    print(f"Taille cible: {TARGET_SIZE}")
    print(f"Mode couleur: L (grayscale) uniquement (radiographies)")
    print(f"Avec masquage: {with_masking}")
    print(f"Normalisation: {normalize_method or 'aucune'}")
    print(f"Classes: {CLASSES}")
    print(f"\n{'='*60}")

    # Statistiques
    total_processed = 0
    errors = []

    # Traiter chaque classe
    for class_name in CLASSES:
        print(f"\nTraitement de la classe: {class_name}")
        
        # Chemins source et sortie
        source_dir = SOURCE_PATH / class_name
        output_dir = OUTPUT_PATH / class_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Utiliser images/ dans tous les cas
        images_dir = source_dir / "images"
        image_files = sorted(images_dir.glob("*.png"))
        
        if with_masking:
            masks_dir = source_dir / "masks"
        
        print(f"Nombre d'images trouvées: {len(image_files)}")
        
        # Traiter chaque image
        for img_path in tqdm(image_files, desc=f"Processing {class_name}"):
            try:
                # Charger l'image
                img = Image.open(img_path).convert('L') # raw resolution = 299x299
                
                if with_masking:
                    # Charger le mask
                    mask_path = masks_dir / img_path.name # same name as image but in masks/
                    mask = Image.open(mask_path).convert('L')
                    
                    # Convertir en arrays OpenCV (grayscale uniquement)
                    img_cv = np.array(img)
                    mask_cv = np.array(mask)
                    
                    # Redimensionner l'image à la taille du mask
                    mask_size = (mask_cv.shape[1], mask_cv.shape[0])  # cv2 utilise (width, height)
                    img_resized_cv = cv2.resize(img_cv, mask_size, interpolation=cv2.INTER_LANCZOS4)
                    
                    # Préparer le mask pour OpenCV (0/255 requis)
                    if mask_cv.max() <= 1:
                        mask_binary = (mask_cv * 255).astype(np.uint8)
                    else:
                        mask_binary = mask_cv.astype(np.uint8)
                    
                    # Appliquer le masquage avec bitwise_and
                    masked_cv = cv2.bitwise_and(img_resized_cv, img_resized_cv, mask=mask_binary)
                    
                    # Reconvertir en PIL Image
                    img = Image.fromarray(masked_cv)
                
                # Convertir en grayscale si nécessaire
                if img.mode != 'L':
                    img = img.convert('L')
                
                # Redimensionner
                img = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
                
                # Normalisation 
                if normalize_method:
                    img_array = np.array(img)
                    img_array = normalize_image(img_array, normalize_method)
                    img = Image.fromarray((img_array * 255).astype(np.uint8))
                
                # Sauvegarder
                output_file = output_dir / img_path.name
                img.save(output_file)
                
                total_processed += 1
                
            except Exception as e:
                errors.append((img_path, str(e)))
        
        print(f"✓ {class_name}: {len(list(output_dir.glob('*.png')))} images créées")

    print(f"\n{'='*60}")
    print(f"RÉSUMÉ")
    print(f"{'='*60}")
    print(f"Total d'images traitées: {total_processed}")
    print(f"Erreurs: {len(errors)}")

    if errors:
        print("\nPremières erreurs:")
        for img, err in errors[:5]:
            print(f"  - {img.name}: {err}")

    # Vérification finale
    print(f"\n{'='*60}")
    print("Nombre d'images par classe dans le nouveau dataset:")
    for class_name in CLASSES:
        class_dir = OUTPUT_PATH / class_name
        n_images = len(list(class_dir.glob("*.png")))
        print(f"  {class_name}: {n_images}")

    print(f"\n✓ Dataset créé avec succès dans: {OUTPUT_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Créer un dataset d'images radiographiques en grayscale avec options de résolution, masquage et normalisation")
    parser.add_argument("--resolution", type=int, default=256, help="Résolution cible (carrée)")
    parser.add_argument("--with_masking", action='store_true', help="Appliquer les masques si activé")
    parser.add_argument("--normalize", choices=['minmax', 'standard'], help="Normaliser les images: minmax=[0,1] ou standard=z-score")
  
    args = parser.parse_args()
    create_dataset(args.resolution, args.with_masking, args.normalize)

