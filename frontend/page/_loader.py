"""Chargement dynamique des pages via importlib — supporte fichiers et packages."""

import importlib.util
from pathlib import Path


def load_pages(page_dir: Path, filenames: list) -> tuple:
    """Charge les modules de pages depuis des fichiers .py ou des packages.

    Un package est détecté si ``page_dir/<nom>/__init__.py`` existe.

    Returns:
        (loaded_pages, import_errors) où loaded_pages est une liste de (fname, mod).
    """
    loaded, errors = [], []
    for fname in filenames:
        pkg_init = page_dir / fname.replace(".py", "") / "__init__.py"
        fpath = pkg_init if pkg_init.exists() else page_dir / fname
        module_name = f"page_{fname.replace('.', '_').replace('/', '_')}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, str(fpath))
            if spec is None or spec.loader is None:
                raise ImportError("spec ou loader est None")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if not hasattr(mod, "run"):
                raise AttributeError(f"Fonction `run()` absente dans {fname}")
            loaded.append((fname, mod))
        except Exception as e:  # pylint: disable=broad-exception-caught
            errors.append((fname, str(e)))
    return loaded, errors
