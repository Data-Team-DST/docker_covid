"""Tests config — fail-fast sur API_KEY vide en production (US production-audit)."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_preprocess_params() -> dict:
    with open(REPO_ROOT / "params.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["preprocess"]


def test_defaults_match_params_yaml_preprocess_section():
    """Les defaults de preprocessing DOIVENT rester synchronisés avec params.yaml (train/
    serving skew sinon). Cette même config existe séparément dans segmentation-service —
    voir le test miroir côté segmentation-service (TODO.md #13, pas de source unique car
    R8 interdit un import Python cross-service pour la partager)."""
    prep = _load_preprocess_params()
    settings = Settings()

    assert settings.img_size == tuple(prep["img_size"])
    assert settings.masking == prep["masking"]
    assert settings.cropping == prep["cropping"]
    assert settings.clahe == prep["clahe"]
    assert settings.clahe_clip_limit == prep["clahe_clip_limit"]
    assert settings.clahe_tile_grid_size == tuple(prep["clahe_tile_grid_size"])
    assert settings.denoising_method == prep["denoising_method"]


def test_production_without_api_key_raises():
    with pytest.raises(ValidationError, match="API_KEY"):
        Settings(api_env="production", api_key="")


def test_production_with_api_key_is_valid():
    settings = Settings(api_env="production", api_key="secret123")
    assert settings.api_key == "secret123"


def test_development_without_api_key_is_valid():
    settings = Settings(api_env="development", api_key="")
    assert settings.api_key == ""
