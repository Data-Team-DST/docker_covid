"""
Tests for the configuration module.
"""

import json

import pytest

from utils.config import (
    Config,
    build_config,
    deep_merge,
    flatten_dict,
    load_config_files,
)


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory with test files."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create default config
    default_config = {
        "paths": {
            "data_dir": "data",
            "models_dir": "models",
        },
        "training": {
            "batch_size": 64,
            "epochs": 100,
        },
    }
    with open(config_dir / "default_config.json", "w") as f:
        json.dump(default_config, f)

    # Create colab config
    colab_config = {
        "training": {
            "batch_size": 32,
            "learning_rate": 0.01,
        }
    }
    with open(config_dir / "colab_config.json", "w") as f:
        json.dump(colab_config, f)

    return tmp_path


def test_config_initialization(tmp_path):
    """Test basic Config class initialization."""
    config = Config(
        project_root=tmp_path,
        data_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
        results_dir=tmp_path / "results",
    )

    assert config.project_root == tmp_path
    assert config.img_width == 256  # Test default value
    assert config.batch_size == 32  # Test default value
    assert isinstance(config.classes, list)


def test_config_post_init(tmp_path):
    """Test post-initialization calculations."""
    config = Config(
        project_root=tmp_path,
        data_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
        results_dir=tmp_path / "results",
        img_width=224,
        img_height=224,
        classes=["class1", "class2"],
    )

    assert config.num_classes == 2
    assert config.img_size == (224, 224)
    assert config.figure_size == (12, 8)  # Default values


def test_config_to_dict(tmp_path):
    """Test configuration serialization to dict."""
    config = Config(
        project_root=tmp_path,
        data_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
        results_dir=tmp_path / "results",
    )

    data = config.to_dict()
    assert isinstance(data["project_root"], str)
    assert isinstance(data["data_dir"], str)
    assert data["img_width"] == 256


def test_config_save(tmp_path):
    """Test configuration saving to JSON."""
    config = Config(
        project_root=tmp_path,
        data_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
        results_dir=tmp_path / "results",
    )

    save_path = tmp_path / "config.json"
    config.save(save_path)

    assert save_path.exists()
    with open(save_path) as f:
        saved_data = json.load(f)
    assert saved_data["project_root"] == str(tmp_path)


def test_deep_merge():
    """Test dictionary deep merge functionality."""
    base = {"a": 1, "b": {"c": 2, "d": 3}}
    override = {"b": {"d": 4, "e": 5}}

    result = deep_merge(base, override)
    assert result["b"]["c"] == 2  # Preserved from base
    assert result["b"]["d"] == 4  # Overridden
    assert result["b"]["e"] == 5  # Added from override


def test_flatten_dict():
    """Test dictionary flattening functionality."""
    nested = {"a": 1, "b": {"c": 2, "d": {"e": 3}}}

    flat = flatten_dict(nested)
    assert flat["a"] == 1
    assert flat["b_c"] == 2
    assert flat["b_d_e"] == 3


def test_load_config_files(temp_config_dir):
    """Test configuration file loading and merging."""
    config_data = load_config_files(temp_config_dir, "colab")

    assert config_data["paths"]["data_dir"] == "data"
    # Verify colab config overrides
    assert config_data["training"]["batch_size"] == 32
    assert abs(config_data["training"]["learning_rate"] - 0.01) < 1e-7


def test_load_config_files_missing(tmp_path):
    """Test handling of missing configuration files."""
    config_data = load_config_files(tmp_path, "colab")
    assert isinstance(config_data, dict)
    assert len(config_data) == 0


def test_build_config(temp_config_dir):
    """Test complete configuration building process."""
    config = build_config(temp_config_dir, "colab")

    assert isinstance(config, Config)
    assert config.batch_size == 32  # From colab config
    assert config.data_dir == temp_config_dir / "data"
    assert config.models_dir == temp_config_dir / "models"


def test_build_config_absolute_paths(temp_config_dir):
    """Test configuration building with absolute paths."""
    # Create config with absolute paths
    with open(temp_config_dir / "config/default_config.json", "w") as f:
        json.dump(
            {
                "paths": {
                    "data_dir": str(temp_config_dir / "custom_data"),
                }
            },
            f,
        )

    config = build_config(temp_config_dir, "default")
    assert config.data_dir == temp_config_dir / "custom_data"


def test_config_validation(tmp_path):
    """Test behaviour when passing non-Path types for some fields."""
    # Passing a string for project_root should not attempt to write to '/' and
    # should preserve the provided value. Use tmp paths for dirs to avoid
    # creating directories at the filesystem root.
    cfg = Config(
        project_root="invalid",
        data_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
        results_dir=tmp_path / "results",
    )

    # project_root remains the provided string
    assert cfg.project_root == "invalid"


def test_environment_handling(temp_config_dir):
    """Test different environment configurations."""
    # Test with default environment
    default_config = build_config(temp_config_dir, "default")
    assert default_config.batch_size == 64

    # Test with colab environment
    colab_config = build_config(temp_config_dir, "colab")
    assert colab_config.batch_size == 32
