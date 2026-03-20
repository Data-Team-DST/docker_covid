# 04_Machine_learning_et_optimisation.py — Fallback si le package est absent.
# Le loader préfère 04_Machine_learning_et_optimisation/__init__.py.
# pylint: disable=invalid-name
# code-smell: max-lines=20 reason="Fallback minimal, délégué au package"

import streamlit as st


def run():
    """Fallback — délégué au package 04_Machine_learning_et_optimisation/."""
    st.info("Page ML et optimisation en cours de chargement…")


if __name__ == "__main__":
    run()
