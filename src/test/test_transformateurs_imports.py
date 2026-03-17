def test_import_transformateurs_module():
    """Vérifie que tous les transformateurs s'importent sans erreur."""
    from src.features.Pipelines import transformateurs

    expected_attrs = {
        "ImageLoader",
        "ImageResizer",
        "ImageNormalizer",
        "ImageMasker",
        "ImageFlattener",
        "ImageBinarizer",
        "ImageAugmenter",
        "ImageRandomCropper",
        "ImageHistogram",
        "ImagePCA",
        "ImageStandardScaler",
        "VisualizeTransformer",
        "SaveTransformer",
    }

    for attr in expected_attrs:
        assert hasattr(transformateurs, attr), f"{attr} manquant"
