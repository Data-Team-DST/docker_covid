"""Affichage des matrices de confusion — évaluation initiale et Grid
Search."""

# code-smell: max-lines=141 reason="2 fonctions affichage matrices"
# pylint: disable=too-many-locals

from pathlib import Path

import streamlit as st
from PIL import Image

MODELS = ["SVM", "KNN", "RF"]


def _load_matrix_map(matrices_folder: Path, n_images: int = 1) -> dict:
    sample_map = {}
    for model_name in MODELS:
        model_path = matrices_folder / model_name
        if model_path.exists():
            img_files = sorted(model_path.glob("*.png")) + sorted(
                model_path.glob("*.jpg")
            )
            sample_map[model_name] = [{"image": str(f)} for f in img_files[:n_images]]
    return sample_map


def render_initial_confusion_matrices(matrices_folder: Path):
    """Display confusion matrices for initial (non-optimised) models."""
    with st.container(border=True):
        st.title("Évaluation des modèles — Matrices de confusion")
        col1, col2 = st.columns([0.5, 0.5], gap="small")
        with col1:
            display_cont = st.container(border=True)
        with col2:
            select_cont = st.container(border=True)

        with select_cont:
            st.subheader("Sélection")
            st.markdown("Les matrices illustrent les performances des modèles évalués.")
            choice = st.selectbox(
                "Modèle :", ["all"] + MODELS, index=0, key="MATRICES_1"
            )
            show_names = st.checkbox(
                "Afficher les noms de fichiers", value=True, key="NAMES1"
            )
            if st.button("Matrices de confusion", key="LOAD1"):
                st.session_state["sample_map_1"] = _load_matrix_map(matrices_folder, 1)

        with display_cont:
            st.markdown("## Matrices de confusion")
            sample_map = st.session_state.get("sample_map_1", {})
            if not sample_map:
                st.info("Cliquez sur le bouton pour afficher les matrices.")
                return
            targets = list(sample_map.keys()) if choice == "all" else [choice]
            for model_name, entries in sample_map.items():
                if model_name in targets and entries:
                    st.markdown(f"### {model_name}")
                    img_path = Path(entries[0]["image"])
                    if img_path.exists():
                        im = Image.open(img_path).convert("RGB")
                        im.thumbnail((500, 500))
                        caption = img_path.name if show_names else "Matrice"
                        st.image(
                            im,
                            caption=caption,
                            output_format="PNG",
                        )


def render_grid_search_matrices(matrices_folder: Path):
    """Display confusion matrices for Grid Search optimised models."""
    with st.container(border=True):
        st.title("Résultats — Matrices de confusion (modèles optimisés)")
        col1, col2 = st.columns([2, 1], gap="small")
        with col1:
            display_cont = st.container(border=True)
        with col2:
            select_cont = st.container(border=True)

        with select_cont:
            choice = st.selectbox(
                "Modèle :", ["all"] + MODELS, index=0, key="MATRICES_2"
            )
            show_names = st.checkbox(
                "Afficher les noms de fichiers", value=True, key="NAMES2"
            )
            if st.button("Matrices de confusion (Grid Search)", key="LOAD2"):
                st.session_state["sample_map"] = _load_matrix_map(matrices_folder, 2)

        with display_cont:
            st.title("Matrices de confusion")
            sample_map = st.session_state.get("sample_map", {})
            if not sample_map:
                st.info("Cliquez sur le bouton pour afficher les matrices.")
                return
            targets = list(sample_map.keys()) if choice == "all" else [choice]
            for model_name, entries in sample_map.items():
                if model_name not in targets:
                    continue
                st.markdown(f"### {model_name} — {len(entries)} matrices")
                cols = st.columns(2)
                for idx, entry in enumerate(entries):
                    img_path = Path(entry["image"])
                    if img_path.exists():
                        with cols[idx % 2]:
                            im = Image.open(img_path).convert("RGB")
                            im.thumbnail((500, 500))
                            caption = (
                                img_path.name if show_names else f"Matrice {idx + 1}"
                            )
                            st.image(
                                im,
                                caption=caption,
                                output_format="PNG",
                                use_container_width=True,
                            )

        st.success(
            "Les hyperparamètres optimaux ont permis d'améliorer"
            " les performances initiales."
        )
