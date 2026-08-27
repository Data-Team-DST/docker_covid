"""Tests unitaires — fonctions ML cœur de la segmentation (ds_covid.segmentation).

TODO.md #11 : ces fonctions n'avaient aucune couverture (seul le pipeline HTTP côté
segmentation-service, qui duplique clean_mask indépendamment, est testé).
"""
import cv2
import numpy as np
import pytest
import tensorflow as tf

from ds_covid.segmentation import (
    clean_mask,
    collect_pairs,
    combined_loss,
    dice_coef,
    dice_loss,
    iou_metric,
    load_pair,
)

# ── dice_coef / dice_loss ────────────────────────────────────────────────────


def test_dice_coef_identical_masks_is_one():
    mask = tf.constant(np.random.randint(0, 2, size=(8, 8, 1)).astype("float32"))
    assert float(dice_coef(mask, mask)) == pytest.approx(1.0, abs=1e-6)


def test_dice_coef_disjoint_masks_is_near_zero():
    y_true = np.zeros((32, 32, 1), dtype="float32")
    y_true[:16] = 1.0
    y_pred = np.zeros((32, 32, 1), dtype="float32")
    y_pred[16:] = 1.0
    dice = float(dice_coef(tf.constant(y_true), tf.constant(y_pred)))
    assert dice == pytest.approx(0.0, abs=1e-2)


def test_dice_loss_is_one_minus_dice_coef():
    y_true = tf.constant(np.random.randint(0, 2, size=(8, 8, 1)).astype("float32"))
    y_pred = tf.constant(np.random.rand(8, 8, 1).astype("float32"))
    expected = 1.0 - float(dice_coef(y_true, y_pred))
    assert float(dice_loss(y_true, y_pred)) == pytest.approx(expected, abs=1e-6)


# ── combined_loss ─────────────────────────────────────────────────────────────


def test_combined_loss_is_finite_and_non_negative():
    y_true = tf.constant(np.random.randint(0, 2, size=(4, 8, 8, 1)).astype("float32"))
    y_pred = tf.constant(np.random.rand(4, 8, 8, 1).astype("float32"))
    loss = combined_loss(y_true, y_pred).numpy()
    assert np.all(np.isfinite(loss))
    assert np.all(loss >= 0)


# ── iou_metric ────────────────────────────────────────────────────────────────


def test_iou_metric_identical_masks_is_one():
    mask = tf.constant(np.random.randint(0, 2, size=(8, 8, 1)).astype("float32"))
    assert float(iou_metric(mask, mask)) == pytest.approx(1.0, abs=1e-6)


def test_iou_metric_disjoint_masks_is_near_zero():
    y_true = np.zeros((32, 32, 1), dtype="float32")
    y_true[:16] = 1.0
    y_pred = np.zeros((32, 32, 1), dtype="float32")
    y_pred[16:] = 1.0
    iou = float(iou_metric(tf.constant(y_true), tf.constant(y_pred)))
    assert iou == pytest.approx(0.0, abs=1e-2)


# ── clean_mask ──────────────────────────────────────────────────────────────


def test_clean_mask_removes_parasite_island():
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[10:30, 10:30] = 255  # composante principale
    mask[50, 50] = 255  # îlot isolé
    cleaned = clean_mask(mask, n_components=1, closing_kernel_size=3)
    assert cleaned[50, 50] == 0
    assert cleaned[20, 20] == 255


def test_clean_mask_shape_and_dtype_preserved():
    mask = np.zeros((32, 32), dtype=np.uint8)
    mask[5:15, 5:15] = 255
    cleaned = clean_mask(mask)
    assert cleaned.shape == mask.shape
    assert cleaned.dtype == np.uint8


def test_clean_mask_empty_mask_returns_empty():
    mask = np.zeros((32, 32), dtype=np.uint8)
    cleaned = clean_mask(mask)
    assert cleaned.max() == 0


# ── collect_pairs ─────────────────────────────────────────────────────────────


def test_collect_pairs_matches_only_images_with_masks(tmp_path):
    classes = {"COVID": 0, "Normal": 1}
    for class_name in classes:
        (tmp_path / class_name / "images").mkdir(parents=True)
        (tmp_path / class_name / "masks").mkdir(parents=True)

    (tmp_path / "COVID" / "images" / "a.png").write_bytes(b"fake")
    (tmp_path / "COVID" / "masks" / "a.png").write_bytes(b"fake")
    (tmp_path / "COVID" / "images" / "b.png").write_bytes(b"fake")  # pas de mask -> exclu
    (tmp_path / "Normal" / "images" / "c.png").write_bytes(b"fake")
    (tmp_path / "Normal" / "masks" / "c.png").write_bytes(b"fake")

    img_paths, mask_paths = collect_pairs(tmp_path, classes)

    assert len(img_paths) == len(mask_paths) == 2
    assert all(m.exists() for m in mask_paths)


def test_collect_pairs_skips_missing_class_dir(tmp_path):
    classes = {"COVID": 0, "Ghost": 1}
    (tmp_path / "COVID" / "images").mkdir(parents=True)
    (tmp_path / "COVID" / "masks").mkdir(parents=True)

    img_paths, mask_paths = collect_pairs(tmp_path, classes)

    assert img_paths == []
    assert mask_paths == []


# ── load_pair ─────────────────────────────────────────────────────────────────


def test_load_pair_resizes_and_normalizes(tmp_path):
    img = np.full((100, 80), 200, dtype=np.uint8)
    mask = np.zeros((100, 80), dtype=np.uint8)
    mask[:50] = 255

    img_path = tmp_path / "img.png"
    mask_path = tmp_path / "mask.png"
    cv2.imwrite(str(img_path), img)
    cv2.imwrite(str(mask_path), mask)

    loaded_img, loaded_mask = load_pair(img_path, mask_path, img_size=32)

    assert loaded_img.shape == (32, 32, 1)
    assert loaded_mask.shape == (32, 32, 1)
    assert loaded_img.max() <= 1.0 and loaded_img.min() >= 0.0
    assert set(np.unique(loaded_mask)).issubset({0.0, 1.0})


def test_load_pair_missing_image_raises(tmp_path):
    mask_path = tmp_path / "mask.png"
    cv2.imwrite(str(mask_path), np.zeros((10, 10), dtype=np.uint8))

    with pytest.raises(FileNotFoundError):
        load_pair(tmp_path / "missing.png", mask_path, img_size=16)


def test_load_pair_missing_mask_raises(tmp_path):
    img_path = tmp_path / "img.png"
    cv2.imwrite(str(img_path), np.zeros((10, 10), dtype=np.uint8))

    with pytest.raises(FileNotFoundError):
        load_pair(img_path, tmp_path / "missing.png", img_size=16)
