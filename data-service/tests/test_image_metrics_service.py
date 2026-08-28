"""Tests image_metrics_service — métriques et échantillonnage (chantier point 15,
logique portée depuis frontend/page/02_donnees/_data_utils.py)."""

import pytest
from PIL import Image

from data_service.image_metrics_service import (
    compute_image_metrics,
    mask_coverage,
    sample_images_from_class,
)


def test_compute_image_metrics_uniform_image_has_zero_entropy():
    img = Image.new("RGB", (16, 16), color=(100, 100, 100))
    metrics = compute_image_metrics(img)
    assert metrics["luminosity_mean"] == 100.0
    assert metrics["contrast_std"] == 0.0
    assert metrics["entropy"] == pytest.approx(0.0, abs=1e-9)


def test_compute_image_metrics_returns_expected_keys():
    img = Image.new("RGB", (8, 8), color=(0, 0, 0))
    metrics = compute_image_metrics(img)
    assert set(metrics.keys()) == {"luminosity_mean", "contrast_std", "entropy"}


def test_mask_coverage_missing_file_returns_none(tmp_path):
    assert mask_coverage(tmp_path / "missing.png") is None


def test_mask_coverage_full_white_mask_is_100_percent(tmp_path):
    mask_path = tmp_path / "mask.png"
    Image.new("L", (10, 10), color=255).save(mask_path)
    assert mask_coverage(mask_path) == 100.0


def test_mask_coverage_full_black_mask_is_zero_percent(tmp_path):
    mask_path = tmp_path / "mask.png"
    Image.new("L", (10, 10), color=0).save(mask_path)
    assert mask_coverage(mask_path) == 0.0


def test_sample_images_from_class_missing_dir_returns_empty(tmp_path):
    assert sample_images_from_class(tmp_path, "COVID", 5) == []


def test_sample_images_from_class_returns_all_when_fewer_than_n(tmp_path):
    images_dir = tmp_path / "COVID" / "images"
    images_dir.mkdir(parents=True)
    (images_dir / "a.png").write_bytes(b"x")
    (images_dir / "b.png").write_bytes(b"x")

    result = sample_images_from_class(tmp_path, "COVID", 5)

    assert len(result) == 2


def test_sample_images_from_class_caps_at_n(tmp_path):
    images_dir = tmp_path / "COVID" / "images"
    images_dir.mkdir(parents=True)
    for i in range(10):
        (images_dir / f"{i}.png").write_bytes(b"x")

    result = sample_images_from_class(tmp_path, "COVID", 3)

    assert len(result) == 3
