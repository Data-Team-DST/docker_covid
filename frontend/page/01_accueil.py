# 01_accueil.py — Accueil détaillé mais oral-friendly

import streamlit as st
from streamlit_extras.colored_header import colored_header
from pathlib import Path


_CSS = """
<style>
:root{ --bg:#0f1115; --card:#131416; --muted:#9aa1a6; --accent:#4fc3f7; }
body, .stApp { background: var(--bg); color: #e6eef6; font-family: "Inter", sans-serif; }
.project-hero { background: linear-gradient(135deg, rgba(10,20,40,0.85), rgba(6,10,20,0.75)); padding: 18px; border-radius: 12px; box-shadow: 0 6px 18px rgba(0,0,0,0.5); color: #e6eef6; }
.card { background: linear-gradient(90deg, rgba(15,23,36,0.95), rgba(10,14,22,0.95)); padding: 14px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.03); box-shadow: 0 4px 10px rgba(0,0,0,0.35); color: #dbe9ff; margin-bottom:10px; }
.card-title { font-weight:700; font-size:14px; margin-bottom:6px; color:#cfe8ff; }
.card-body { font-size:13px; color:#98a7bf; }
.small-note { font-size:12px; color:#98a1b3; }
.kv { font-size:12px; color:var(--muted); }
abbr { text-decoration: none; border-bottom: 1px dotted rgba(255,255,255,0.12); cursor: help; }
@media (max-width:720px){ .project-hero { padding:12px; } .card { padding:10px; } }
</style>
"""

def run():
    st.markdown(_CSS, unsafe_allow_html=True)

    # Header
    try:
        colored_header(
            label="Analyse de radiographies pulmonaires — Classification COVID-19 et aide au diagnostic",
            description="Projet réalisé par Cirine B., Lena B., Steven M., Rafael C., encadré par Nicolas M.",
            color_name="blue-70"
        )
    except Exception:
        st.markdown("<h2>Analyse de radiographies pulmonaires — Classification COVID-19</h2>", unsafe_allow_html=True)
        st.markdown("<div class='small-note'>Prototype d'assistance diagnostique visuelle — rapide, interprétable et prêt pour la démonstration.</div>", unsafe_allow_html=True)

    st.divider()

    # Contexte
    st.markdown("### Contexte de l’épidémie de COVID-19")
    st.markdown(
        "<div class='project-hero'>"
        "<strong>Bilan mondial</strong><br>"
        "• Trois ans d’épidémie mondiale<br>"
        "• Plus de <strong>700 millions</strong> de cas<br>"
        "• Plus de <strong>7 millions</strong> de décès<br>"
        "• Pneumonie virale spécifique (<em>viral pneumonia</em>) due au <strong>SARS-CoV-2</strong>"
        "</div>",
        unsafe_allow_html=True
    )

    # Problème 1 + Solution 1
    st.markdown(
        "<div class='project-hero'>"
        "<strong>Problème 1 : limites des tests <abbr title='Reverse Transcription PCR'>RT-PCR</abbr></strong><br>"
        "• Tests lents, sensibilité variable, dépendance aux laboratoires<br>"
        "<strong>Solution :</strong> imagerie médicale (CXR/CT) pour un triage rapide et accessible."
        "</div>",
        unsafe_allow_html=True
    )

    # Images et diagnostic visuel
    img_col, text_col = st.columns([1, 2])
    with img_col:
        images_data = {
            "Fig1": ("Fig1.jpg", "Opacités en verre dépoli périphériques bilatérales."),
            "Fig2": ("Fig2.jpg", "Consolidation pulmonaire sévère bilatérale."),
            "Fig3": ("Fig3.jpg", "Progression radiologique COVID-19."),
            "Fig4": ("Fig4.jpg", "Évolution temporelle des atteintes pulmonaires."),
        }
        selected_fig = st.selectbox("Sélectionner une image :", list(images_data.keys()))
        img_name, caption = images_data[selected_fig]
        img_path = Path(__file__).parent / "images" / "covid_cxr_symptoms" / img_name
        if img_path.exists(): st.image(str(img_path), caption=caption)
        else: st.info("Image non disponible.")

    with text_col:
        st.markdown(
            "<div class='project-hero'>"
            "<strong>Difficulté du diagnostic visuel</strong><br>"
            "Les patterns radiologiques du COVID-19 sont proches d’autres pneumonies virales, complexe même pour des radiologues expérimentés.<br><br>"
            "<strong>Problème 2 : surcharge des radiologues</strong><br>"
            "Volume d’examens élevé → temps réduit par examen.<br><br>"
            "<strong>Solution : intelligence artificielle</strong><br>"
            "Machine learning et deep learning accélèrent la détection, tout en proposant une solution interprétable et reproductible."
            "</div>",
            unsafe_allow_html=True
        )

    st.divider()
    st.markdown(
        "Avant de présenter les résultats, précisons des objectifs clairs, mesurables et adaptés à un cadre exploratoire."
    )

    # Objectifs SMART
    st.markdown("## Objectifs SMART")
    # col1, col2 = st.columns(2)
    # with col1:
    st.subheader("Objectif 1 — Performance")
    st.markdown(
            "- **S** : classification COVID vs non-COVID\n"
            "- **M** : F1 ≥ 0,80 sur validation indépendante\n"
            "- **A** : fine-tuning InceptionV3\n"
            "- **R** : réduire faux négatifs\n"
            "- **T** : 12/01/2024 démonstration"
        )
    # with col2:
    #     st.subheader("Objectif 2 — Sensibilité / Spécificité ")
    #     st.markdown(
    #         "- **S** : maximiser détection positives\n"
    #         "- **M** : matrice de confusion pour comparaison\n"
    #         "- **A** : ajustement seuils et calibration\n"
    #         "- **R** : réduire faux négatifs\n"
    #         "- **T** : démontré sur validation"
    #     )

if __name__ == "__main__":
    run()