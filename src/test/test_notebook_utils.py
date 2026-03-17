"""
Tests for the notebook utilities module.
"""

from pathlib import Path

import numpy as np
import pytest

from keras.utils import to_categorical

from utils import (
    build_custom_cnn,
    build_transfer_learning_model,
    compile_model,
    compute_class_weights,
    create_callbacks,
    create_data_generators,
    create_preprocessing_pipeline,
    evaluate_model,
    get_preprocessing_function,
    load_dataset,
    plot_confusion_matrix,
    plot_training_curves,
    prepare_train_val_test_split,
    run_gradcam_analysis,
    select_sample_images,
    setup_interpretability,
    train_model,
    unfreeze_top_layers,
)



# Fixtures
@pytest.fixture
def sample_data():
    """Create sample data for testing."""
    rng = np.random.default_rng(42)
    X = rng.random((100, 224, 224, 3))
    y = rng.integers(0, 2, 100)
    return X, y


@pytest.fixture
def sample_model():
    """Create a sample model for testing."""
    model = build_custom_cnn(input_shape=(224, 224, 3), num_classes=2)
    return model


# Test Data Loading & Preprocessing
def test_load_dataset():
    """Test dataset loading function."""
    # Call with non-existing dir; should return empty lists
    image_paths, _mask_paths, _labels, labels_int = load_dataset(
        Path("nonexistent"), categories=["cat1"], verbose=False
    )

    assert isinstance(image_paths, list)
    assert isinstance(labels_int, np.ndarray)


def test_create_preprocessing_pipeline():
    """Test preprocessing pipeline creation."""
    pipeline = create_preprocessing_pipeline()
    # sklearn Pipeline has attribute 'steps'
    assert hasattr(pipeline, "steps")
    assert isinstance(pipeline.steps, list)


def test_prepare_train_val_test_split(sample_data):
    """Test data splitting function."""
    X, y = sample_data
    splits = prepare_train_val_test_split(
        X, y, num_classes=2, val_size=0.2, test_size=0.2
    )
    assert len(splits) == 6  # Should return 6 arrays


def test_compute_class_weights(sample_data):
    """Test class weights computation."""
    _, y = sample_data
    weights = compute_class_weights(
        y, categories=["class0", "class1"], verbose=False
    )
    assert isinstance(weights, dict)


# Test Model Building
def test_build_custom_cnn():
    """Test custom CNN model building."""
    model = build_custom_cnn(input_shape=(224, 224, 3), num_classes=2)
    assert model is not None


def test_compile_model(sample_model):
    """Test model compilation."""
    compiled_model = compile_model(sample_model)
    assert compiled_model.optimizer is not None


def test_create_callbacks():
    """Test callback creation."""
    # Provide a temporary models directory
    import tempfile

    tmpdir = Path(tempfile.mkdtemp())
    callbacks = create_callbacks(tmpdir, verbose=False)
    assert len(callbacks) > 0


def test_build_transfer_learning_model():
    """Test transfer learning model building."""
    input_shape = (224, 224, 3)
    model, base = build_transfer_learning_model(
        input_shape=input_shape, num_classes=2, verbose=False
    )
    assert model is not None
    assert base is not None


def test_unfreeze_top_layers():
    """Test layer unfreezing using a transfer learning model."""
    model, base_model = build_transfer_learning_model(
        input_shape=(224, 224, 3), num_classes=2, verbose=False
    )
    compiled = compile_model(model, verbose=False)
    unfrozen_model = unfreeze_top_layers(
        base_model, compiled, n_layers=5, verbose=False
    )
    assert unfrozen_model is not None


# Test Training & Evaluation
def test_train_model(sample_model, sample_data):
    """Test model training."""
    X, y = sample_data
    # Prepare simple generators
    x_train, y_train = X[:60], y[:60]
    x_val, y_val = X[60:80], y[60:80]

    y_train_cat = to_categorical(y_train, num_classes=2)
    y_val_cat = to_categorical(y_val, num_classes=2)

    train_gen, val_gen, _ = create_data_generators(
        x_train,
        y_train_cat,
        x_val,
        y_val_cat,
        batch_size=16,
        augment_train=False,
        verbose=False,
    )

    compiled = compile_model(sample_model, verbose=False)
    history = train_model(
        compiled, train_gen, val_gen, epochs=1, callbacks=[], verbose=False
    )
    assert history is not None


def test_evaluate_model(sample_model, sample_data):
    """Test model evaluation."""
    X, y = sample_data
    # Compile model and create a small test set
    compiled = compile_model(sample_model, verbose=False)
    x_test, y_test = X[80:100], y[80:100]
    y_test_cat = to_categorical(y_test, num_classes=2)
    metrics = evaluate_model(
        compiled,
        (x_test, y_test_cat),
        class_names=["class0", "class1"],
        verbose=False,
    )
    assert isinstance(metrics, dict)
    assert "y_true" in metrics


# Test Visualization
def test_plot_training_curves():
    """Test training curves plotting."""
    class DummyHistory:
        def __init__(self):
            self.history = {"loss": [0.5, 0.3], "val_loss": [0.6, 0.4]}

    res = plot_training_curves(DummyHistory())
    assert res is None


def test_plot_confusion_matrix():
    """Test confusion matrix plotting."""
    y_true = np.array([0, 1, 0, 1])
    y_pred = np.array([0, 1, 1, 1])
    res = plot_confusion_matrix(
        y_true, y_pred, class_names=["class0", "class1"]
    )
    assert res is None


# Test Interpretability
def test_setup_interpretability(sample_model):
    """Test interpretability setup."""
    gradcam = setup_interpretability(sample_model, verbose=False)
    assert gradcam is not None
    assert hasattr(gradcam, "compute_heatmap")


def test_run_gradcam_analysis(sample_model, sample_data):
    """Test Grad-CAM analysis."""
    X, _ = sample_data
    gradcam = setup_interpretability(sample_model, verbose=False)
    # simple indices and descriptions
    indices = [0, 1]
    descriptions = ["sample 1", "sample 2"]
    class_names = ["class0", "class1"]
    y_pred_probs = np.ones((len(X), 2)) * 0.5
    res = run_gradcam_analysis(
        gradcam,
        X,
        indices,
        descriptions,
        class_names,
        y_pred_probs=y_pred_probs,
    )
    assert res is None


def test_select_sample_images(sample_data):
    """Test sample image selection."""
    X, y = sample_data
    # Use identical predictions to get correctly classified samples
    indices, _ = select_sample_images(
        X, y, y, ["class0", "class1"], n_samples=2
    )
    assert isinstance(indices, (list, np.ndarray))


def test_get_preprocessing_function():
    """Test preprocessing function retrieval."""
    preprocess_fn = get_preprocessing_function("InceptionV3")
    assert callable(preprocess_fn)
