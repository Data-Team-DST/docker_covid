"""Page 04 — Machine learning et optimisation."""

# pylint: disable=invalid-name,wrong-import-position,import-error

import os
import sys
from pathlib import Path

import streamlit as st
from streamlit_extras.colored_header import colored_header

_HERE = Path(__file__).parent
if str(_HERE) in sys.path:
    sys.path.remove(str(_HERE))
sys.path.insert(0, str(_HERE))
for _k in ["_sections", "_confusion_matrices"]:
    sys.modules.pop(_k, None)

from _confusion_matrices import (  # noqa: E402
    render_grid_search_matrices,
    render_initial_confusion_matrices,
)
from _sections import (  # noqa: E402
    render_feature_extraction,
    render_grid_search_params,
    render_model_list,
    render_optimization,
)

_IMG_DIR = os.path.join(Path(__file__).parent.parent.parent, "page", "images") + os.sep
_MATRICES_FOLDER = Path(_IMG_DIR) / "matrices_confusion"


def run():
    """Point d'entrée de la page machine learning."""
    colored_header(
        label="Modèles de machine learning et optimisation",
        color_name="blue-70",
    )
    st.divider()
    render_feature_extraction(_IMG_DIR)
    st.divider()
    render_model_list()
    render_initial_confusion_matrices(_MATRICES_FOLDER)
    st.divider()
    render_optimization()
    st.divider()
    render_grid_search_params(_IMG_DIR)
    st.divider()
    render_grid_search_matrices(_MATRICES_FOLDER)


if __name__ == "__main__":
    run()
