# code-smell: max-lines=155 reason="Suite tests ML: baseline+prédiction+évaluation"
"""Tests unitaires — modèles ML de base, prédiction et évaluation."""

import numpy as np
import pytest
from sklearn.ensemble import (
    AdaBoostClassifier,
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.svm import LinearSVC

from src.ml.baseline import AdaBoost, GradientBoosting, LinearSVM, RandomForest
from src.ml.evaluate import compute_metrics, top_class
from src.ml.predict import predict_from_features, predict_proba_from_features


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def synthetic_dataset():
    """Dataset synthétique : 60 samples, 20 features, 2 classes."""
    rng = np.random.default_rng(42)
    X = rng.standard_normal((60, 20))
    y = (X[:, 0] > 0).astype(int)
    return X, y


@pytest.fixture
def fitted_rf(synthetic_dataset):
    """RandomForest entraîné sur le dataset synthétique."""
    X, y = synthetic_dataset
    model = RandomForest()
    model.fit(X, y)
    return model


# ── Factories baseline ───────────────────────────────────────────────────────


def test_random_forest_type():
    assert isinstance(RandomForest(), RandomForestClassifier)


def test_linear_svm_type():
    assert isinstance(LinearSVM(), LinearSVC)


def test_adaboost_type():
    assert isinstance(AdaBoost(), AdaBoostClassifier)


def test_gradient_boosting_type():
    assert isinstance(GradientBoosting(), GradientBoostingClassifier)


def test_random_forest_random_state():
    assert RandomForest().random_state == 42


def test_random_forest_n_estimators():
    assert RandomForest().n_estimators == 100


# ── Fit + predict ────────────────────────────────────────────────────────────


def test_random_forest_fit_predict_shape(synthetic_dataset):
    X, y = synthetic_dataset
    model = RandomForest()
    model.fit(X, y)
    preds = model.predict(X)
    assert preds.shape == (60,)


def test_random_forest_predict_classes(synthetic_dataset):
    X, y = synthetic_dataset
    model = RandomForest()
    model.fit(X, y)
    assert set(model.predict(X)).issubset({0, 1})


def test_predict_from_features_shape(synthetic_dataset, fitted_rf):
    X, _ = synthetic_dataset
    preds = predict_from_features(fitted_rf, X)
    assert preds.shape == (60,)


def test_predict_proba_shape(synthetic_dataset, fitted_rf):
    X, _ = synthetic_dataset
    probas = predict_proba_from_features(fitted_rf, X)
    assert probas is not None
    assert probas.shape == (60, 2)


def test_predict_proba_sums_to_one(synthetic_dataset, fitted_rf):
    X, _ = synthetic_dataset
    probas = predict_proba_from_features(fitted_rf, X)
    assert np.allclose(probas.sum(axis=1), 1.0, atol=1e-6)


def test_predict_proba_none_for_svm(synthetic_dataset):
    """LinearSVC n'a pas predict_proba — doit retourner None."""
    X, y = synthetic_dataset
    model = LinearSVM()
    model.fit(X, y)
    assert predict_proba_from_features(model, X) is None


# ── Évaluation ───────────────────────────────────────────────────────────────


def test_compute_metrics_keys(synthetic_dataset, fitted_rf):
    X, y = synthetic_dataset
    metrics = compute_metrics(y, fitted_rf.predict(X))
    assert {"accuracy", "report", "confusion_matrix"} == set(metrics.keys())


def test_compute_metrics_accuracy_range(synthetic_dataset, fitted_rf):
    X, y = synthetic_dataset
    metrics = compute_metrics(y, fitted_rf.predict(X))
    assert 0.0 <= metrics["accuracy"] <= 1.0


def test_compute_metrics_confusion_matrix_shape(synthetic_dataset, fitted_rf):
    X, y = synthetic_dataset
    cm = compute_metrics(y, fitted_rf.predict(X))["confusion_matrix"]
    assert len(cm) == 2 and len(cm[0]) == 2


def test_compute_metrics_with_class_names(synthetic_dataset, fitted_rf):
    X, y = synthetic_dataset
    report = compute_metrics(
        y, fitted_rf.predict(X), class_names=["Non-COVID", "COVID"]
    )["report"]
    assert "COVID" in report


def test_top_class_correct_label():
    probas = np.array([0.1, 0.7, 0.2])
    cls, conf = top_class(probas, ["A", "B", "C"])
    assert cls == "B"


def test_top_class_correct_confidence():
    probas = np.array([0.1, 0.7, 0.2])
    _, conf = top_class(probas, ["A", "B", "C"])
    assert abs(conf - 0.7) < 1e-6
