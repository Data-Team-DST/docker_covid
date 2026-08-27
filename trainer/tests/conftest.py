"""Rend `ds_covid` importable sans dépendre de testpaths/pythonpath racine (trainer/
n'est pas câblé dans [tool.pytest.ini_options] du pyproject.toml, cf. TODO.md #11)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
