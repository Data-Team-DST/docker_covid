# 01_accueil.py — Fallback si le package 01_accueil/ est absent.
# Le loader (_loader.py) préfère 01_accueil/__init__.py quand il existe.
# code-smell: max-lines=20 reason="Fallback minimal, délégué au package 01_accueil/"
# pylint: disable=invalid-name

import streamlit as st


def run():
    """Fallback — délégué au package 01_accueil/."""
    st.markdown("## Analyse de radiographies pulmonaires")
    st.divider()
    st.info("Page en cours de chargement…")


if __name__ == "__main__":
    run()
