"""Wrapper logging data-service — délègue à shared/logging_config.py."""
import logging
import sys
from pathlib import Path

# Permet l'import de shared/ depuis la racine du projet
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from shared.logging_config import setup_logging as _setup  # noqa: E402


def setup_logging(log_dir: Path | None = None) -> None:  # noqa: ARG001
    _setup(service_name="data-service")
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
