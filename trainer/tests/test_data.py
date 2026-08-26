"""Tests unitaires — MemmapSequence (ds_covid.data), partagée classification/segmentation.

TODO.md #11 : zéro couverture avant ce chantier.
"""
import numpy as np

from ds_covid.data import MemmapSequence


def test_len_is_ceil_of_indices_over_batch_size():
    X = np.zeros((10, 4, 4, 1), dtype="float32")
    y = np.zeros((10,), dtype="float32")
    seq = MemmapSequence(X, y, batch_size=3, shuffle=False)
    assert len(seq) == 4  # ceil(10/3)


def test_getitem_returns_batches_from_full_dataset():
    X = np.arange(10).reshape(10, 1, 1, 1).astype("float32")
    y = np.arange(10).astype("float32")
    seq = MemmapSequence(X, y, batch_size=4, shuffle=False)

    X_batch, y_batch = seq[0]
    assert X_batch.shape[0] == 4
    assert list(y_batch) == [0, 1, 2, 3]


def test_getitem_respects_subset_indices():
    X = np.arange(10).reshape(10, 1, 1, 1).astype("float32")
    y = np.arange(10).astype("float32")
    seq = MemmapSequence(X, y, batch_size=2, shuffle=False, indices=np.array([5, 6, 7]))

    assert len(seq) == 2  # ceil(3/2)
    _, y_batch0 = seq[0]
    assert list(y_batch0) == [5, 6]


def test_shuffle_true_changes_order_after_epoch_end():
    X = np.arange(20).reshape(20, 1, 1, 1).astype("float32")
    y = np.arange(20).astype("float32")

    np.random.seed(0)
    seq = MemmapSequence(X, y, batch_size=20, shuffle=True)
    order_before = seq.indices.copy()

    np.random.seed(1)
    seq.on_epoch_end()
    order_after = seq.indices.copy()

    assert not np.array_equal(order_before, order_after)


def test_shuffle_false_keeps_original_order():
    X = np.arange(5).reshape(5, 1, 1, 1).astype("float32")
    y = np.arange(5).astype("float32")
    seq = MemmapSequence(X, y, batch_size=5, shuffle=False)

    seq.on_epoch_end()

    assert list(seq.indices) == [0, 1, 2, 3, 4]


def test_class_weight_produces_sample_weight_per_label():
    X = np.zeros((4, 1, 1, 1), dtype="float32")
    y = np.array([0, 1, 0, 1], dtype="float32")
    seq = MemmapSequence(X, y, batch_size=4, shuffle=False, class_weight={0: 1.0, 1: 2.0})

    _, _, sample_weight = seq[0]

    assert list(sample_weight) == [1.0, 2.0, 1.0, 2.0]


def test_no_class_weight_returns_two_tuple():
    X = np.zeros((4, 1, 1, 1), dtype="float32")
    y = np.array([0, 1, 0, 1], dtype="float32")
    seq = MemmapSequence(X, y, batch_size=4, shuffle=False)

    result = seq[0]

    assert len(result) == 2
