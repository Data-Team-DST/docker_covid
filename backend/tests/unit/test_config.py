"""Tests config — fail-fast sur API_KEY vide en production (US production-audit)."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_production_without_api_key_raises():
    with pytest.raises(ValidationError, match="API_KEY"):
        Settings(api_env="production", api_key="")


def test_production_with_api_key_is_valid():
    settings = Settings(api_env="production", api_key="secret123")
    assert settings.api_key == "secret123"


def test_development_without_api_key_is_valid():
    settings = Settings(api_env="development", api_key="")
    assert settings.api_key == ""
