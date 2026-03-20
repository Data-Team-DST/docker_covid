# 06_cicd.py — Fallback si le package 06_cicd/ est absent.
# Le loader (_loader.py) préfère 06_cicd/__init__.py quand il existe.
# pylint: disable=invalid-name
# code-smell: max-lines=30 reason="Fallback minimal, délégué au package 06_cicd/"

import streamlit as st
from streamlit_extras.colored_header import colored_header


def run():
    """Fallback — délégué au package 06_cicd/."""
    colored_header(
        label="CI/CD et qualité logicielle",
        description="Présentation du pipeline CI réel : objectifs, outils, limites.",
        color_name="blue-70",
    )
    st.divider()
    st.info("Page en cours de chargement…")


if __name__ == "__main__":
    run()
