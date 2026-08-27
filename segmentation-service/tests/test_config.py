"""Tests config — cohérence avec params.yaml (TODO.md #13)."""
from pathlib import Path

import yaml

from segmentation_service.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_params() -> dict:
    with open(REPO_ROOT / "params.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_defaults_match_params_yaml():
    """Les defaults DOIVENT rester synchronisés avec params.yaml (train/serving skew
    sinon). Cette même config existe séparément dans backend/app/config.py — voir le test
    miroir côté backend (TODO.md #13 ; pas de source unique car R8 interdit un import
    Python cross-service pour la partager)."""
    params = _load_params()
    prep = params["preprocess"]
    seg = params["segmentation"]
    settings = Settings()

    img_h, img_w = prep["img_size"]
    assert img_h == img_w, (
        "segmentation_service.config.Settings.img_size est un int unique (résolution "
        "carrée supposée) — un img_size non carré dans params.yaml invaliderait cette "
        "hypothèse et ce test ne le détecterait pas correctement sans cette assertion"
    )
    assert settings.img_size == img_h
    assert settings.clean_mask_components == seg["clean_mask_components"]
    assert settings.clean_mask_closing_kernel == seg["clean_mask_closing_kernel"]


def test_mlflow_model_name_matches_params_yaml():
    """mlflow_model_name DOIT rester synchronisé avec params.yaml
    (mlflow.segmentation_model_name) — sinon la Registry est interrogée sous un nom
    que rien n'y enregistre jamais."""
    mlflow_params = _load_params()["mlflow"]
    settings = Settings()

    assert settings.mlflow_model_name == mlflow_params["segmentation_model_name"]
