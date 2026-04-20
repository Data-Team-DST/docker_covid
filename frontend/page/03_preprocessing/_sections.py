"""Sections de la page 03_preprocessing : environnements, masking,
déséquilibre, augmentation."""

# code-smell: max-lines=140 reason="4 sections UI de preprocessing cohésives"
# pylint: disable=missing-function-docstring

import streamlit as st


def render_environments(img_dir: str):
    container = st.container(border=True)
    with container:
        st.title("Environnements de travail")
        windows_col, wsl_col, collab_col = st.columns(3)
        with windows_col:
            with st.container(border=True):
                st.header("Windows")
                st.success("Environnement simple")
                st.info("Données stockées localement")
                st.error("Pas de compatibilité GPU")
        with wsl_col:
            with st.container(border=True):
                st.header("WSL")
                st.warning("Configuration plus complexe, CUDA à installer")
                st.info("Données stockées localement")
                st.warning("Compatibilité GPU (cartes Nvidia)")
        with collab_col:
            with st.container(border=True):
                st.header("Google Colab")
                st.error("Environnement le plus complexe")
                st.warning("Données stockées sur le cloud (Drive)")
                st.success("Compatibilité GPU / TPU")

        auto_cont = st.container(border=True)
        with auto_cont:
            c1, c2 = st.columns([0.5, 0.5], gap="small")
            with c1:
                with st.container(border=True):
                    st.header("Configuration automatique")
                    st.write(
                        "Script permettant de détecter et configurer"
                        " automatiquement l'environnement."
                    )
                    st.image(
                        f"{img_dir}config_auto_env.png",
                        caption="Configuration automatique",
                    )
            with c2:
                with st.container(border=True):
                    st.header("Configuration WSL")
                    st.write(
                        "Étapes nécessaires à la configuration"
                        " de l'environnement WSL."
                    )
                    st.image(
                        f"{img_dir}config_wsl.PNG",
                        caption="Configuration WSL",
                    )


def render_masking(img_dir: str):
    with st.container(border=True):
        st.title("Masking des images")
        col_1, col_2 = st.columns([0.2, 0.2], gap="small")
        with col_1:
            sub_1, sub_2 = st.columns(2)
            with sub_1:
                st.image(
                    f"{img_dir}covid_before_mask.png",
                    caption="Avant application du masque",
                )
            with sub_2:
                st.image(
                    f"{img_dir}covid_after_mask.png",
                    caption="Après application du masque",
                )
            st.info("Quoi ? Application d'un masque pour isoler la région d'intérêt.")
            st.info("Pourquoi ? Réduire le bruit et améliorer la qualité des données.")
            st.info("Comment ? Utilisation d'algorithmes de segmentation.")
            st.info("Impact ? Amélioration potentielle des performances du modèle.")
            st.info("Tests associés ? Comparaison avant / après application du masque.")
        with col_2:
            st.image(
                f"{img_dir}arbo_augmented.png",
                caption="Arborescence automatique du dataset",
            )


def render_class_balance(img_dir: str):
    with st.container(border=True):
        st.title("Gestion du déséquilibre de classes")
        col_1, col_2 = st.columns([0.3, 0.3], gap="small")
        with col_1:
            with st.container(border=True):
                st.title("Stratégie de rééquilibrage")
                st.image(
                    f"{img_dir}strategie_reequilibrage.PNG",
                    caption="Stratégie de rééquilibrage",
                )
        with col_2:
            with st.container(border=True):
                st.title("Stratified Split")
                st.image(
                    f"{img_dir}split_stratifie.PNG",
                    caption="Découpage stratifié",
                )
        with st.container(border=True):
            st.title("Configuration du dataset")
            st.image(
                f"{img_dir}config_dataset.PNG",
                caption="Configuration du dataset",
            )


def render_augmentation(img_dir: str):
    with st.container(border=True):
        st.title("Data Augmentation")
        col_1, col_2 = st.columns([0.5, 0.5], gap="small")
        with col_1:
            st.image(
                f"{img_dir}config_data_augmentation.PNG",
                caption="Configuration de la data augmentation",
            )
        with col_2:
            st.image(
                f"{img_dir}visu_augmentation.PNG",
                caption="Visualisation des augmentations",
            )
