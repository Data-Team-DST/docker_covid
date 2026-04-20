"""Sections de la page 04 — extraction, évaluation et optimisation ML."""

# pylint: disable=missing-function-docstring,implicit-str-concat

import streamlit as st


def render_feature_extraction(img_dir: str):
    with st.container(border=True):
        st.title("Extraction des caractéristiques")
        col1, col2 = st.columns([0.5, 0.5], gap="small")
        with col1:
            with st.container(border=True):
                st.subheader("ML Feature Preparation")
                st.image(
                    f"{img_dir}prep_ML_features.PNG",
                    caption="ML Feature Preparation",
                )
        with col2:
            with st.container(border=True):
                st.subheader("ML Results Overview")
                st.image(
                    f"{img_dir}result_ml.PNG",
                    caption="ML Results Overview",
                )


def render_model_list():
    with st.container(border=True):
        st.title("Évaluation des modèles de machine learning")
        with st.container(border=True):
            st.subheader("Les modèles de machine learning testés dans notre projet")
            st.info("Support Vector Machine (SVM)")
            st.info("k-Nearest Neighbors (k-NN)")
            st.info("Random Forest")
        with st.container(border=True):
            st.subheader("Méthodologie d'évaluation des modèles")
            st.info("Un échantillon équilibré de 200 données par classe a été utilisé.")
            st.info(
                "L'évaluation repose sur le calcul de la matrice de"
                " confusion, outil permettant de visualiser les"
                " performances d'un classificateur."
            )


def render_optimization():
    with st.container(border=True):
        st.title("Optimisation des modèles de machine learning")
        st.success("Random Forest : modèle le plus performant.")
        st.error("SVM : modèle le moins performant.")
        st.info(
            "Objectifs de l'optimisation :\n"
            "- Renforcer l'efficacité et améliorer les performances\n"
            "- Obtenir une analyse comparative complète"
        )


def render_grid_search_params(img_dir: str):
    with st.container(border=True):
        st.title("Optimisation par Grid Search")
        st.info(
            "Grid Search teste toutes les combinaisons"
            " d'hyperparamètres sur une grille prédéfinie.\n\n"
            "L'évaluation repose sur une validation croisée (k-fold)."
        )
        st.divider()
        col1, col2 = st.columns([0.5, 0.5], gap="small")
        with col1:
            with st.container(border=True):
                st.subheader("Hyperparamètres testés")
                st.info("SVM : C (régularisation), nombre maximal d'itérations")
                st.info("Random Forest : nombre d'arbres, profondeur maximale, etc.")
        with col2:
            with st.container(border=True):
                st.subheader("Sauvegarde JSON")
                st.info("Les hyperparamètres ont été sauvegardés dans un fichier JSON.")
                from pathlib import Path  # noqa: PLC0415

                image_path = Path(f"{img_dir}parametres.png").relative_to(Path.cwd())
                st.image(
                    str(image_path),
                    caption="Hyperparamètres",
                    use_container_width=True,
                )
