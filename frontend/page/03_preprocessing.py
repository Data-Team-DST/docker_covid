# 03_preprocessing.py

import os

# Imports système
from pathlib import Path

import streamlit as st

# Structure comments:
# - Expose only run().
# - Cette page documente chaque transformation appliquée
#   (quoi, pourquoi, comment, impact, tests).
# - Tous les blocs sont des placeholders à remplacer
#   par des descriptions projet réelles.



def run():

    # colored_header(
    #     label="Preprocessing — Description & Justification",
    #     description=(
    #         "Documenter chaque transformation : quoi, pourquoi, "
    #         "comment, impact et tests associés."
    #     ),
    #     color_name="blue-70"
    # )

    st.divider()

    # Obtenir le chemin global du projet
    chemin_global = Path(__file__).parent.parent
    # Ajouter /page/images/ au chemin global
    chemin_global = os.path.join(chemin_global, "page", "images/")

    p5 = rf"{chemin_global}config_dataset.PNG"
    p6 = rf"{chemin_global}config_wsl.PNG"
    p7 = rf"{chemin_global}strategie_reequilibrage.PNG"
    p8 = rf"{chemin_global}split_stratifie.PNG"
    p9 = rf"{chemin_global}config_data_augmentation.PNG"
    p10 = rf"{chemin_global}visu_augmentation.PNG"

    Config_container = st.container(border=True)
    with Config_container:
        st.title("Environnements de travail")

        p11 = rf"{chemin_global}config_auto_env.png"

        windows_col, wsl_col, collab_col = st.columns(3)

        with windows_col:
            windows_cont = st.container(border=True)
        with wsl_col:
            wsl_cont = st.container(border=True)
        with collab_col:
            collab_cont = st.container(border=True)

        with windows_cont:
            st.header("Windows")
            st.success("Environnement simple")
            st.info("Données stockées localement")
            st.error("Pas de compatibilité GPU")

        with wsl_cont:
            st.header("WSL")
            st.warning("Configuration plus complexe, CUDA à installer")
            st.info("Données stockées localement")
            st.warning("Compatibilité GPU (cartes Nvidia)")

        with collab_cont:
            st.header("Google Colab")
            st.error("Environnement le plus complexe")
            st.warning("Données stockées sur le cloud (Drive)")
            st.success("Compatibilité GPU / TPU")

        config_auto_container = st.container(border=True)
        with config_auto_container:
            config_col1, config_col2 = st.columns([0.5, 0.5], gap="small")

            with config_col1:
                config_1_container = st.container(border=True)
                with config_1_container:
                    st.header("Configuration automatique")
                    st.write(
                        "Script permettant de détecter et de configurer "
                        "automatiquement l’environnement de travail."
                    )
                    st.image(p11, caption="Configuration automatique")

            with config_col2:
                config_2_container = st.container(border=True)
                with config_2_container:
                    st.header("Configuration WSL")
                    st.write(
                        "Étapes nécessaires à la configuration "
                        "de l’environnement WSL pour le projet."
                    )
                    st.image(str(p6), caption="Configuration WSL")

    st.divider()

    # Masking des images
    p1 = rf"{chemin_global}covid_before_mask.png"
    p2 = rf"{chemin_global}covid_after_mask.png"
    p3 = rf"{chemin_global}arbo_augmented.png"

    Masking_container = st.container(border=True)
    with Masking_container:
        st.title("Masking des images")

        col_1, col_2 = st.columns([0.2, 0.2], gap="small")

        with col_1:
            sub_col_1, sub_col_2 = st.columns(2)

            with sub_col_1:
                st.image(str(p1), caption="Avant application du masque")

            with sub_col_2:
                st.image(str(p2), caption="Après application du masque")

            st.info(
                "Quoi ? Application d’un masque pour isoler la région d’intérêt."
            )
            st.info(
                "Pourquoi ? Réduire le bruit et améliorer la qualité des données "
                "en se concentrant sur les zones pertinentes."
            )
            st.info(
                "Comment ? Utilisation d’algorithmes de segmentation pour "
                "générer et appliquer le masque."
            )
            st.info(
                "Impact ? Amélioration potentielle des performances du modèle "
                "en réduisant les informations non pertinentes."
            )
            st.info(
                "Tests associés ? Comparaison des performances du modèle "
                "avant et après application du masque."
            )

        with col_2:
            st.image(str(p3), caption="Arborescence automatique du dataset")

    st.divider()

    # Gestion du déséquilibre de classes
    desequilibre_container = st.container(border=True)
    with desequilibre_container:
        st.title("Gestion du déséquilibre de classes")

        des_col_1, des_col_2 = st.columns([0.3, 0.3], gap="small")

        with des_col_1:
            reeq_container = st.container(border=True)
            with reeq_container:
                st.title("Stratégie de rééquilibrage")
                st.image(str(p7), caption="Stratégie de rééquilibrage")

        with des_col_2:
            split_strat_container = st.container(border=True)
            with split_strat_container:
                st.title("Stratified Split")
                st.image(str(p8), caption="Découpage stratifié")

        dataset_config_cont = st.container(border=True)
        with dataset_config_cont:
            st.title("Configuration du dataset")
            st.image(str(p5), caption="Configuration du dataset")

    st.divider()

    # Data augmentation
    augmentation_container = st.container(border=True)
    with augmentation_container:
        st.title("Data Augmentation")

        aug_col_1, aug_col_2 = st.columns([0.5, 0.5], gap="small")

        with aug_col_1:
            st.image(str(p9), caption="Configuration de la data augmentation")

        with aug_col_2:
            st.image(str(p10), caption="Visualisation des augmentations")
