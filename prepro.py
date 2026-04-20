"""
Notes de développement :

Numpy : Image (H, W) i.e (lignes, colonnes)
cv2 : Image (W, H) 


"""

import argparse
from pathlib import Path
from PIL import Image
import numpy as np
import cv2
from tqdm import tqdm

# Configuration

PROJECT_ROOT = Path(__file__).parent
SOURCE_PATH = PROJECT_ROOT / "data" / "raw" / "COVID-19_Radiography_Dataset"


def normalize_image(img_array: np.ndarray, method='minmax') -> np.ndarray:
    """
    Normalise une image selon la méthode choisie.

    Warning : La normalisation est faite dans le pipeline d'entraînement car impossible de stocker des images normalisées (float32) en PNG.
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

def squared_crop_to_lungs(masked_img: np.ndarray) -> np.ndarray:
    """
    Rogne l'image masquée pour ne garder que la région contenant les poumons, puis ajoute du padding pour obtenir une image carrée.
     Cela permet de recentrer les poumons et de réduire le bruit de fond, tout en préservant un format carré pour les étapes suivantes du pipeline.
     
    Args:
         masked_img: np.array (H, W) - image après masquage, avec des pixels de poumon > 0 et le reste à 0
         
    Returns:
         np.array - image rognée et paddée pour être carrée, centrée sur les poumons

    Raises:
         ValueError - si l'image masquée ne contient aucun pixel non nul
    """

    # On ne garde que les pixels de poumon (i.e non noirs)

    rows = np.any(masked_img > 0, axis=1) # lignes contenant au moins un pixel > 0, rows is like [False, True, True, False, ...]
    cols = np.any(masked_img > 0, axis=0) # colonnes contenant au moins un pixel > 0, cols is like [False, True, True, False, ...]

    if not rows.any() or not cols.any():
        raise ValueError("L'image masquée ne contient aucun pixel de poumon (tous les pixels sont à zéro)")
    
    r1, r2 = np.where(rows)[0][[0, -1]] # indices de la première et dernière ligne contenant du poumon

    # np.where(rows)[0] gives the indices of rows that are True, and [0, -1] selects the first and last of those indices.

    c1, c2 = np.where(cols)[0][[0, -1]] # indices de la première et dernière colonne contenant du poumon

    h, w   = r2 - r1 + 1, c2 - c1 + 1

    side   = max(h, w)

    cy, cx = (r1 + r2) // 2, (c1 + c2) // 2

    y1 = max(0, cy - side // 2)
    x1 = max(0, cx - side // 2)
    y2 = min(masked_img.shape[0], y1 + side)
    x2 = min(masked_img.shape[1], x1 + side)

    # Si x2 ou y2 a été clampé, on réajuste x1 et y1 pour garder un carré de la bonne taille

    y1, x1 = max(0, y2 - side), max(0, x2 - side) 

    return masked_img[y1:y2, x1:x2]

def process_single_image(
        img_path: Path,
        mask_path: Path | None, 
        cropping: bool,
        denoising_method: str | None, # if None we skip denoising
        clahe_processor: cv2.CLAHE | None, # if None we skip CLAHE
        target_size: int) -> np.ndarray:
    
    """

    Applique le pipeline de prétraitement à une seule image, selon les options choisies.

    ** On ne manipule que des images en L (grayscale) car ce sont des radiographies. **

    Pipeline complet détaillé :

    1) chargement des raw data : l'image (299x299) et son Mask (256x256)

    1) a) [OPTIONNEL] Denoising avec une méthode comme Gaussian Blur, si jamais la qualité des images est mauvaise (pas notre cas, curated dataset, mais pourrait être le cas d'une image donnée dans predict/)

    2) Resize du Mask vers (299x299) pour fitter image. On utilise une interpolation de type INTER_NEAREST pour ne pas créer des valeurs autres que 0 ou 1

    3) Masking (multiplication pixel par pixel)

    4) Crop (rogner l'image masquée) puis padding pour retrouver une image carrée

    5) CLAHE pour améliorer contraste local de l'image

    6) Resize final vers le target size (ex : 128x128 ou 256x256) avec interpolation de type LANCZOS4 pour préserver les détails

    Args:
         img_path: Path - chemin vers l'image à traiter
         mask_path: Path | None - chemin vers le mask correspondant, ou None pour ne pas faire de masking
         cropping: bool - appliquer le crop+padding pour recentrer les poumons si True (seulement actif si mask_path n'est pas None)
         denoising_method: str | None - méthode de denoising à appliquer (ex: 'gaussian') ou None pour aucune
         clahe_processor: cv2.CLAHE | None - instance de cv2.CLAHE à appliquer, ou None pour ne pas faire de CLAHE
         target_size: int - résolution cible (carrée) pour l'image finale (ex: 128, 256)
         
    Returns:
         np.ndarray - image traitée au format numpy array, prête à être sauvegardée

    Raises:
         FileNotFoundError - si l'image ou le mask (si masking activé) ne peuvent pas être chargés
         ValueError - si le crop est activé mais que l'image masquée ne contient aucun pixel de poumon (tous les pixels sont à zéro)
    """

    # Charger l'image

    img_array  = cv2.imread(str(img_path),  cv2.IMREAD_GRAYSCALE)   # raw resolution = 299x299, L (1 channel) or fake RGB (3 channels identiques), valeurs 0-255
                                                                    # img_array est un array numpy
    if img_array is None:
        raise FileNotFoundError(f"Impossible de charger l'image: {img_path}")
    
    # Denoising (optionnel)
    if denoising_method == 'gaussian':

        img_array = cv2.GaussianBlur(img_array, (5, 5), 0)      # cv2.GaussianBlur(src, ksize, sigmaX) - ksize doit être impair, sigmaX est l'écart type du noyau gaussien
                                                                # outputs an array of the same shape as img_array, with values denoised

    # Masking, cropping, padding (optionnel)

    if mask_path:


        mask_array = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)   # raw resolution = 256x256, fake RGB (3 channels identiques), binaire : 0 | 255

                                                                        # mask_array est un array numpy 
        
        if mask_array is None:
            raise FileNotFoundError(f"Impossible de charger le mask: {mask_path}")
        
        # Redimensionner le mask à la taille de l'image (299x299) avec interpolation nearest pour garder les valeurs binaires

        mask_array = cv2.resize(mask_array, (img_array.shape[1], img_array.shape[0]), interpolation=cv2.INTER_NEAREST) # (width, height) order for cv2.resize argument. Output is still a numpy array

        # Préparer le mask pour OpenCV (0/255 requis)

        if mask_array.max() <= 1: # Should not be the case with our images, but just in case
            mask_binary = (mask_array * 255).astype(np.uint8)
        else:
            mask_binary = mask_array.astype(np.uint8)
        
        # Appliquer le masquage avec bitwise_and
        masked_array = cv2.bitwise_and(img_array, img_array, mask=mask_binary) # cv2.bitwise_and(src1, src2, mask) - effectue une opération AND bit à bit entre src1 et src2, en utilisant le mask pour ne garder que les pixels où mask est non nul. Renvoie un array de la même forme que img_array, avec les pixels de poumon conservés et le reste mis à zéro.
        
        # Optionnel : recadrage + padding pour recentrer les poumons
        if cropping:
            masked_array = squared_crop_to_lungs(masked_array)

        img_array = masked_array
    
    # CLAHE (optionnel)

    if clahe_processor:
        img_array = clahe_processor.apply(img_array)
    
    # Redimensionner (cv2) avec LANCZOS4 pour préserver les détails
    img_array = cv2.resize(img_array, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4)

  
    return img_array # uint8 (H, W)



def preprocess_pipeline(
    denoising_method: str | None,
    masking: bool,
    cropping: bool,
    clahe: bool,
    target_size: int,
    source_path: Path=SOURCE_PATH,
                    ):

    """
    Applique le pipeline de preprocesssing sur le raw dataset pour créer un nouveau dataset d'images radiographiques, avec options à chaque étape.

    Voir pipeline détaillé dans process_single_image() pour les étapes appliquées à chaque image.

    Args:
        denoising_method: str | None - méthode de denoising à appliquer (ex: 'gaussian') ou None pour aucune
        masking: bool - appliquer le masquage si True
        cropping: bool - appliquer le crop+padding pour recentrer les poumons si True
        clahe: bool - appliquer CLAHE pour améliorer le contraste local si True
        target_size: int - résolution cible (carrée) pour les images finales (ex: 128, 256)
        source_path: Path - chemin vers le dataset raw
    """

    # We generate the dataset name based on the options chosen, to keep track of different versions
    dataset_name_parts = [f"{target_size}x{target_size}_L"]
    if masking:
        dataset_name_parts.append("masked")
    if cropping:
        dataset_name_parts.append("cropped")
    if clahe:
        dataset_name_parts.append("clahe")

    OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "_".join(dataset_name_parts)

    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

    # Paramètres
    

    CLASSES = ["COVID", "Normal", "Lung_Opacity", "Viral Pneumonia"]

    print(f"Dataset source: {source_path}")
    print(f"Dataset de sortie: {OUTPUT_PATH}")
    print(f"Taille cible: {target_size}x{target_size}")
    print(f"Mode couleur: L (grayscale) uniquement (radiographies)")
    print(f"Avec masquage: {masking}")
    print(f"Avec recadrage: {cropping}")
    print(f"Avec CLAHE: {clahe}")
    print(f"Avec denoising: {denoising_method if denoising_method else 'aucun'}")

    print(f"Classes: {CLASSES}")
    print(f"\n{'='*60}")

    # Statistiques
    total_processed = 0
    errors = []

    
    
    clahe_processor = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)) if clahe else None

    # Traiter chaque classe
    for class_name in CLASSES:
        print(f"\nTraitement de la classe: {class_name}")
        
        # Chemins source et sortie
        source_dir = source_path / class_name
        output_dir = OUTPUT_PATH / class_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Utiliser images/ dans tous les cas
        images_dir = source_dir / "images"
        image_files = sorted(images_dir.glob("*.png"))

        print(f"Nombre d'images trouvées: {len(image_files)}")
        
        if masking:
            masks_dir = source_dir / "masks"
        

        # Traiter chaque image
        for img_path in tqdm(image_files, desc=f"Processing {class_name}"):

            try:
                mask_path = masks_dir / img_path.name if masking else None # same name as image but in masks/

                img_processed_array = process_single_image(
                    img_path=img_path,
                    mask_path=mask_path,
                    cropping=cropping,
                    denoising_method=denoising_method,
                    clahe_processor=clahe_processor,
                    target_size=target_size
                )

                # Sauvegarder avec PIL

                output_file = output_dir / img_path.name
                img_pil = Image.fromarray(img_processed_array)
                img_pil.save(output_file)
                
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

