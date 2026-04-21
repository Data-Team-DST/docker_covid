"""Wrapper logging backend — délègue à shared/logging_config.py."""
from shared.logging_config import setup_logging as _setup  # noqa: E402


def setup_logging() -> None:
    _setup(service_name="backend")
