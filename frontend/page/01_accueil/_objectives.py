"""Page 01 — Section objectifs SMART."""

import streamlit as st


def render_objectives():
    """Affiche les objectifs SMART du projet."""
    st.markdown(
        "Avant de présenter les résultats, précisons des objectifs clairs, "
        "mesurables et adaptés à un cadre exploratoire."
    )
    st.markdown("## Objectifs SMART")
    st.subheader("Objectif 1 — Performance")
    st.markdown(
        "- **S** : classification COVID vs non-COVID\n"
        "- **M** : F1 ≥ 0,80 sur validation indépendante\n"
        "- **A** : fine-tuning InceptionV3\n"
        "- **R** : réduire faux négatifs\n"
        "- **T** : 12/01/2024 démonstration"
    )
