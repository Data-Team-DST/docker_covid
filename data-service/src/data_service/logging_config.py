"""Wrapper logging data-service — délègue à shared/logging_config.py."""
import logging

from shared.logging_config import setup_logging as _setup


def setup_logging(log_dir: Path | None = None) -> None:  # noqa: ARG001
    _setup(service_name="data-service")
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
