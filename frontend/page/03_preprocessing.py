# 03_preprocessing.py — Fallback si le package 03_preprocessing/ est absent.
# Le loader préfère 03_preprocessing/__init__.py quand il existe.
# pylint: disable=invalid-name
# code-smell: max-lines=20 reason="Fallback minimal, délégué au package"

import streamlit as st


def run():
    """Fallback — délégué au package 03_preprocessing/."""
    st.info("Page preprocessing en cours de chargement…")


if __name__ == "__main__":
    run()
