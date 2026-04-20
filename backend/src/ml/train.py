"""Pipeline d'entraînement ML avec tracking MLflow."""

import os

import mlflow
import mlflow.sklearn
from src.ml.baseline import AdaBoost, GradientBoosting, LinearSVM, RandomForest
from src.ml.evaluate import compute_metrics
from src.ml.trainer import split_data, train_with_grid_search

_MODELS = {
    "RandomForest": (RandomForest(), {"n_estimators": [50, 100, 200]}),
    "LinearSVM": (LinearSVM(), {}),
    "AdaBoost": (AdaBoost(), {}),
    "GradientBoosting": (GradientBoosting(), {}),
}


def run_experiment(X, y, experiment_name="ds_covid_baseline", class_names=None):
    """Lance tous les modèles baseline avec tracking MLflow.

    Args:
        X: Features extraites (n_samples, n_features).
        y: Labels encodés (n_samples,).
        experiment_name: Nom de l'expérience MLflow.
        class_names: Noms des classes pour le rapport.

    Returns:
        Liste de dicts {model, accuracy, report, confusion_matrix}.
    """
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    mlflow.set_experiment(experiment_name)

    X_train, X_test, y_train, y_test = split_data(X, y)
    results = []

    for model_name, (model, param_grid) in _MODELS.items():
        with mlflow.start_run(run_name=model_name):
            trained = train_with_grid_search(model, param_grid, X_train, y_train)
            metrics = compute_metrics(
                y_test, trained.predict(X_test), class_names=class_names
            )
            mlflow.log_param("model_type", model_name)
            mlflow.log_metric("accuracy", metrics["accuracy"])
            mlflow.sklearn.log_model(trained, artifact_path=model_name)
            results.append({"model": model_name, **metrics})

    return results
