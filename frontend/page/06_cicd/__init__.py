"""Page 06 — CI/CD et qualité logicielle."""

# pylint: disable=invalid-name,wrong-import-position,import-error

import sys
from pathlib import Path

import streamlit as st
from streamlit_extras.colored_header import colored_header

_HERE = Path(__file__).parent
if str(_HERE) in sys.path:
    sys.path.remove(str(_HERE))
sys.path.insert(0, str(_HERE))
for _k in ["_sections"]:
    sys.modules.pop(_k, None)

from _sections import render_cicd_content  # noqa: E402


def run():
    """Point d'entrée de la page CI/CD."""
    colored_header(
        label="CI/CD et qualité logicielle",
        description=(
            "Présentation du pipeline CI réel : objectifs, outils, "
            "limites pédagogiques, et positionnement académique."
        ),
        color_name="blue-70",
    )
    st.divider()
    render_cicd_content()


if __name__ == "__main__":
    run()
