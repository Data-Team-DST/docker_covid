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
for _k in [
    "_sections",
    "_pipeline_ui",
    "_pipeline_create",
    "_pipeline_load",
    "_pipeline_steps",
    "_pipeline_exec",
]:
    sys.modules.pop(_k, None)

from _pipeline_ui import render_pipeline_section  # noqa: E402
from _sections import render_cicd_content  # noqa: E402

_PROJECT_ROOT = str(Path(__file__).parent.parent.parent.parent)


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

    show_pipe_cont = st.container(border=True)
    with show_pipe_cont:
        st.subheader("Organisation du code et Amélioration")
        st.info(
            "Pour résoudre les problématiques d'organisation, "
            "un Système de Pipelines Sklearn/Streamlit a été développé."
        )
        use_pipeline = st.checkbox("Afficher la section Pipeline Sklearn", value=False)

    render_cicd_content()

    if use_pipeline:
        pipeline_container = st.container(border=True)
        with pipeline_container:
            render_pipeline_section(_PROJECT_ROOT)


if __name__ == "__main__":
    run()
