"""Wrapper logging backend — délègue à shared/logging_config.py."""
import sys
from pathlib import Path

# Permet l'import de shared/ depuis la racine du projet
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.logging_config import setup_logging as _setup  # noqa: E402


def setup_logging() -> None:
    _setup(service_name="backend")
