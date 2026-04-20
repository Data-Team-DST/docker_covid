# 02_donnees.py — Fallback si le package 02_donnees/ est absent.
# Le loader (_loader.py) préfère 02_donnees/__init__.py quand il existe.
# pylint: disable=invalid-name

# code-smell: max-lines=20 reason="Fallback minimal, délégué au package"

import streamlit as st


def run():
    """Fallback — délégué au package 02_donnees/."""
    st.info("Page données en cours de chargement…")


if __name__ == "__main__":
    run()
