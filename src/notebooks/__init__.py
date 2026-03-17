"""
Notebook utilities module.

Provides reusable functions for Jupyter notebooks:
- Data loading and preprocessing
- Model building (Custom CNN & Transfer Learning)
- Training and evaluation
- Visualization
- Interpretability (Grad-CAM)

Organized into focused modules:
- data_utils: Data loading, preprocessing, generators
- model_builders: Custom CNN & Transfer Learning model construction
- training_utils: Training and evaluation
- visualization_utils: Plotting functions
- interpretability_utils: Grad-CAM and analysis
"""

# Data loading & preprocessing
from .data_utils import (
    load_dataset,
    create_preprocessing_pipeline,
    prepare_train_val_test_split,
    compute_class_weights,
    create_data_generators,
    create_transfer_learning_generators,
)

# Model building
from .model_builders import (
    build_custom_cnn,
    build_simple_cnn,
    build_medium_cnn,
    build_deep_cnn,
    compile_model,
    create_callbacks,
    build_transfer_learning_model,
    unfreeze_top_layers,
)

# Training & evaluation
from .training_utils import (
    train_model,
    evaluate_model,
)

# Visualization
from .visualization_utils import (
    plot_training_curves,
    plot_confusion_matrix,
)

# Interpretability
from .interpretability_utils import (
    setup_interpretability,
    run_gradcam_analysis,
    select_sample_images,
    get_preprocessing_function,
)

__all__ = [
    # Data
    "load_dataset",
    "create_preprocessing_pipeline",
    "prepare_train_val_test_split",
    "compute_class_weights",
    "create_data_generators",
    "create_transfer_learning_generators",
    # Model building
    "build_custom_cnn",
    "build_simple_cnn",
    "build_medium_cnn",
    "build_deep_cnn",
    "compile_model",
    "create_callbacks",
    "build_transfer_learning_model",
    "unfreeze_top_layers",
    # Training
    "train_model",
    "evaluate_model",
    # Visualization
    "plot_training_curves",
    "plot_confusion_matrix",
    # Interpretability
    "setup_interpretability",
    "run_gradcam_analysis",
    "select_sample_images",
    "get_preprocessing_function",
]
