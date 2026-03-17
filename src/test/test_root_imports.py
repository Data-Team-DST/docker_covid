def test_import_root_module():
    """Vérifie que le module racine s'importe sans erreur."""
    import src

    # Le module src doit au moins exposer 'features'
    assert hasattr(src, "features")

    # Et vérifier que Pipelines est bien accessible via src.features
    from src import features

    assert hasattr(features, "Pipelines")
