"""Page 01 — Section contexte COVID et diagnostic visuel."""

# pylint: disable=line-too-long

from pathlib import Path

import streamlit as st


def render_context():
    """Affiche le contexte épidémique et les images diagnostiques."""
    st.markdown("### Contexte de l'épidémie de COVID-19")
    st.markdown(
        "<div class='project-hero'>"
        "<strong>Bilan mondial</strong><br>"
        "• Trois ans d'épidémie mondiale<br>"
        "• Plus de <strong>700 millions</strong> de cas<br>"
        "• Plus de <strong>7 millions</strong> de décès<br>"
        "• Pneumonie virale spécifique due au <strong>SARS-CoV-2</strong>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='project-hero'>"
        "<strong>Problème 1 : limites des tests RT-PCR</strong><br>"
        "• Tests lents, sensibilité variable, dépendance aux laboratoires<br>"
        "<strong>Solution :</strong> imagerie médicale (CXR/CT) pour un triage rapide."
        "</div>",
        unsafe_allow_html=True,
    )
    _render_image_selector()
    st.divider()


def _render_image_selector():
    """Affiche le sélecteur d'images radiographiques."""
    images_data = {
        "Fig1": (
            "Fig1.jpg",
            "Opacités en verre dépoli périphériques bilatérales.",
        ),
        "Fig2": ("Fig2.jpg", "Consolidation pulmonaire sévère bilatérale."),
        "Fig3": ("Fig3.jpg", "Progression radiologique COVID-19."),
        "Fig4": ("Fig4.jpg", "Évolution temporelle des atteintes pulmonaires."),
    }
    img_col, text_col = st.columns([1, 2])
    with img_col:
        selected = st.selectbox("Sélectionner une image :", list(images_data.keys()))
        img_name, caption = images_data[selected]
        img_path = (
            Path(__file__).parent.parent / "images" / "covid_cxr_symptoms" / img_name
        )
        if img_path.exists():
            st.image(str(img_path), caption=caption)
        else:
            st.info("Image non disponible.")
    with text_col:
        st.markdown(
            "<div class='project-hero'>"
            "<strong>Difficulté du diagnostic visuel</strong><br>"
            "Les patterns radiologiques du COVID-19 sont proches d'autres pneumonies.<br><br>"
            "<strong>Problème 2 : surcharge des radiologues</strong><br>"
            "Volume élevé → temps réduit par examen.<br><br>"
            "<strong>Solution : IA</strong><br>"
            "ML et deep learning accélèrent la détection de façon interprétable."
            "</div>",
            unsafe_allow_html=True,
        )
