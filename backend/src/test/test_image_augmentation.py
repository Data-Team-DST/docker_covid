import numpy as np  # type: ignore

from features.Pipelines.transformateurs.image_augmentation import (
    ImageAugmenter,
    ImageRandomCropper,
)


def test_image_augmenter_basic():
    """Teste que l'ImageAugmenter transforme
    bien un lot d'images sans erreur."""
    rng = np.random.default_rng(42)
    images = rng.random((5, 64, 64, 3))  # 5 images RGB 64x64

    augmenter = ImageAugmenter(
        flip_horizontal=True,
        flip_vertical=True,
        rotation_range=15,
        brightness_range=(0.8, 1.2),
        noise_std=0.01,
        zoom_range=(0.9, 1.1),
        probability=1.0,  # applique l’augmentation à chaque image
        verbose=False,
        seed=42,
    )

    augmenter.fit(images)
    images_aug = augmenter.transform(images)

    # Vérifie que la forme est identique
    assert images_aug.shape == images.shape
    # Vérifie que le contenu a changé (statistiquement probable)
    assert not np.allclose(images_aug, images)


def test_image_random_cropper_random():
    """Vérifie que le crop aléatoire fonctionne
    et garde les bonnes dimensions."""
    rng = np.random.default_rng(42)
    images = rng.random((3, 128, 128, 3))

    cropper = ImageRandomCropper(
        crop_size=(64, 64),
        mode="random",
        padding=0,
        verbose=False,
        seed=123,
    )
    cropper.fit(images)
    cropped = cropper.transform(images)

    # Doit renvoyer la même quantité d'images
    assert cropped.shape[0] == images.shape[0]
    # Vérifie les dimensions des crops
    assert cropped.shape[1:3] == (64, 64)


def test_image_random_cropper_too_small_warning(caplog):
    """Test : si une image est plus petite que le crop,
    elle est conservée et un warning est loggé."""
    small_image = np.random.rand(1, 32, 32, 3)
    cropper = ImageRandomCropper(crop_size=(64, 64), verbose=False)
    with caplog.at_level("WARNING"):
        cropped = cropper.transform(small_image)
    assert cropped.shape == small_image.shape
    assert any("smaller than crop size" in msg for msg in caplog.messages)
