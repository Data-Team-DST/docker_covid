"""Page 03 — Preprocessing : masking, déséquilibre de classes,
augmentation."""

# pylint: disable=invalid-name,wrong-import-position,import-error

import os
import sys
from pathlib import Path

import streamlit as st

_HERE = Path(__file__).parent
if str(_HERE) in sys.path:
    sys.path.remove(str(_HERE))
sys.path.insert(0, str(_HERE))
for _k in ["_sections"]:
    sys.modules.pop(_k, None)

from _sections import (  # noqa: E402
    render_augmentation,
    render_class_balance,
    render_environments,
    render_masking,
)

_IMG_DIR = os.path.join(Path(__file__).parent.parent.parent, "page", "images") + os.sep


def run():
    """Point d'entrée de la page preprocessing."""
    st.divider()
    render_environments(_IMG_DIR)
    st.divider()
    render_masking(_IMG_DIR)
    st.divider()
    render_class_balance(_IMG_DIR)
    st.divider()
    render_augmentation(_IMG_DIR)


if __name__ == "__main__":
    run()
