"""Pipeline Sklearn — point d'entrée et setup de l'environnement."""

# pylint: disable=import-error

import os
import sys

import streamlit as st


def render_pipeline_section(project_root: str):
    """Affiche la section pipeline interactive (chargement ou création)."""
    data_dir, save_dir = _setup_paths(project_root)
    st.session_state["project_root"] = project_root

    st.title("Exploration et exécution de pipelines Sklearn")
    st.header("⚙️ Configuration")

    if os.path.exists(data_dir):
        labels = [
            d
            for d in os.listdir(data_dir)
            if os.path.isdir(os.path.join(data_dir, d, "images"))
        ]
        st.success("✅ Données trouvées")
        st.info(f"📊 Labels: {', '.join(labels)}")
    else:
        st.error("❌ Répertoire de données introuvable")

    mode = st.radio(
        "Mode de travail:",
        ["📂 Charger un pipeline existant", "🆕 Créer un nouveau pipeline"],
        index=0,
    )

    from _pipeline_create import render_create_mode  # noqa: PLC0415
    from _pipeline_load import render_load_mode  # noqa: PLC0415

    if mode == "📂 Charger un pipeline existant":
        render_load_mode(save_dir)
    else:
        render_create_mode(data_dir, save_dir)


def _setup_paths(project_root: str) -> tuple:
    """Ajoute project_root au sys.path et retourne (data_dir, save_dir)."""
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    data_dir = os.path.join(
        project_root,
        "data",
        "raw",
        "COVID-19_Radiography_Dataset",
        "COVID-19_Radiography_Dataset",
    )
    save_dir = os.path.join(project_root, "models")
    os.makedirs(save_dir, exist_ok=True)
    return data_dir, save_dir
