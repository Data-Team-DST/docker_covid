def test_import_pipelines_module():
    """Vérifie que le module Pipelines s'importe correctement."""
    from src.features import Pipelines

    assert hasattr(Pipelines, "transformateurs")
