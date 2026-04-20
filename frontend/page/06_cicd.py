# 08_cicd_pipeline.py — Présentation CI/CD pédagogique

import os
import sys

import numpy as np

# Imports Pipeline Sklearn
import pandas as pd
import streamlit as st
from sklearn.pipeline import Pipeline
from streamlit_extras.colored_header import colored_header


def run():
    # Header
    colored_header(
        label="CI/CD et qualité logicielle",
        description=(
            "Présentation du pipeline CI réel : objectifs, outils, limites pédagogiques, "
            "et positionnement académique."
        ),
        color_name="blue-70",
    )
    st.divider()

    cicd_container = st.container(border=True)
    show_pipe_cont = st.container(border=True)
    with show_pipe_cont:
        st.subheader("Organisation du code et Amélioration")
        st.info(
            "Pour résoudre les problématiques d'organisation, un Système de Pipelines Sklearn/Streamlit a été développé. "
        )
        USE_PIPELINE_PAGE = st.checkbox(
            "Afficher la section Pipeline Sklearn", value=False
        )
    if USE_PIPELINE_PAGE:
        pipeline_container = st.container(border=True)

    with cicd_container:
        # --- Section 1 : Pourquoi CI/CD ---
        st.markdown("## 1. Pourquoi un pipeline CI/CD ?")
        st.markdown(
            "Même sans déploiement industriel, nous avons mis en place des pratiques de **qualité, "
            "reproductibilité et maintenabilité**. L’objectif est d’éviter le code fragile, "
            "les régressions et la dette technique."
        )
        st.divider()

        # --- Section 2 : Pipeline CI implémenté ---
        st.markdown("## 2. Pipeline CI")
        st.markdown(
            "Exécuté automatiquement via GitHub Actions à chaque push/PR :"
        )
        st.markdown(
            "- Linting Python avec pylint (score ≥ 8)\n"
            "- Tests unitaires avec pytest\n"
            "- Rapports de couverture\n"
            "- Analyse statique SonarCloud"
        )
        st.divider()

        # --- Section 3 : Philosophie qualité ---
        st.markdown("## 3. Philosophie qualité & tests")
        st.markdown(
            "Approche pragmatique : priorité à la lisibilité, robustesse et détection précoce des régressions. "
            "Tests ciblés sur les composants critiques, couverture volontairement modeste mais contrôlée."
        )
        st.divider()

        # --- Section 4 : Artefacts et traçabilité ---
        st.markdown("## 4. Artefacts produits")
        st.markdown(
            "- Rapports pytest (coverage.xml)\n"
            "- Analyses SonarCloud\n"
            "- Logs GitHub Actions\n"
            "- Historique des exécutions CI"
        )
        st.divider()

        # --- Section 5 : Limites volontaires ---
        st.markdown("## 5. Limites assumées")
        st.markdown(
            "Certains éléments classiques ne sont pas implémentés par choix pédagogique :\n"
            "- Pas de build Docker\n"
            "- Pas de CD / déploiement continu\n"
            "- Pas d’orchestration Kubernetes\n"
            "- Pas de monitoring temps réel\n\n"
            "→ Cohérent avec le périmètre académique et les ressources disponibles."
        )
        st.divider()

        # --- Section 6 : Perspectives ---
        st.markdown("## 6. Perspectives")
        st.markdown(
            "- Introduction progressive de Docker\n"
            "- Séparation CI / CD\n"
            "- Déploiement contrôlé en test\n"
            "- Monitoring basique performances/dérives"
        )
        st.divider()

        # --- Section 7 : Positionnement final ---
        st.markdown("## 7. Positionnement final")
        st.markdown(
            "- Pipeline CI réel, orienté qualité\n"
            "- Au-delà des exigences minimales\n"
            "- Adapté à un projet académique avancé\n"
            "- Base crédible pour industrialisation future"
        )
        st.divider()

    # --- Section 8 : Pipeline Sklearn ---

    # # --- Container principal pour présentation pipeline ---
    # # show_pipe_cont = st.container(border=True)
    # with show_pipe_cont:
    #     st.subheader("Organisation du code et amélioration")
    #     st.info(
    #         "Pour résoudre les problématiques d’organisation, un système de pipelines "
    #         "Sklearn / Streamlit a été développé."
    #     )

    #     # --- Checkbox pour activer la section pipeline ---
    #     USE_PIPELINE_PAGE = st.checkbox(
    #         "Afficher la section Pipeline Sklearn",
    #         value=False
    #     )

    if USE_PIPELINE_PAGE:
        st.divider()
        with pipeline_container:

            st.title("Exploration et exécution de pipelines Sklearn")

            # Ajouter le répertoire racine du projet au chemin Python
            project_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..")
            )
            if project_root not in sys.path:
                sys.path.insert(0, project_root)

            # Import des transformateurs (ordre intentionnel : src avant joblib pour unpickling)
            import joblib  # noqa: I001
            from src.features.St_Pipeline.Transformateurs import (  # noqa: I001 Loaders; Preprocessing; Analyse et features; Utilities
                ImageAnalyser,
                ImageAugmenter,
                ImageFlattener,
                ImageHistogram,
                ImageMasker,
                ImageNormalizer,
                ImagePathLoader,
                ImagePCA,
                ImageResizer,
                RGB_to_L,
                SaveTransformer,
                TrainTestSplitter,
                TupleToDataFrame,
            )

            # Configuration des chemins
            save_dir_paths = os.path.join(project_root, "models")
            data_dir = os.path.join(
                project_root,
                "data",
                "raw",
                "COVID-19_Radiography_Dataset",
                "COVID-19_Radiography_Dataset",
            )

            # Créer le dossier models s'il n'existe pas
            os.makedirs(save_dir_paths, exist_ok=True)
            st.header("⚙️ Configuration")

            # Vérification du répertoire de données
            if os.path.exists(data_dir):
                st.success("✅ Données trouvées")
                labels = [
                    d
                    for d in os.listdir(data_dir)
                    if os.path.isdir(os.path.join(data_dir, d, "images"))
                ]
                st.info(f"📊 Labels: {', '.join(labels)}")
            else:
                st.error("❌ Répertoire de données introuvable")
                # st.stop()
            # Mode de sélection
            mode = st.radio(
                "Mode de travail:",
                [
                    "📂 Charger un pipeline existant",
                    "🆕 Créer un nouveau pipeline",
                ],
                index=0,
            )

            # ============================================================
            # MODE 1: CHARGER UN PIPELINE EXISTANT
            # ============================================================
            if mode == "📂 Charger un pipeline existant":
                pkl_files = [
                    f for f in os.listdir(save_dir_paths) if f.endswith(".pkl")
                ]

                if not pkl_files:
                    st.warning(
                        f"⚠️ Aucun pipeline trouvé dans `{save_dir_paths}`"
                    )
                    st.info(
                        "💡 Créez un nouveau pipeline ou utilisez le notebook pour en générer."
                    )
                    # st.stop()

                # Container sélection
                container_selection = st.container(border=True)
                with container_selection:
                    col1, col2 = st.columns([1, 2])

                    with col1:
                        st.markdown("### 📋 Sélection")
                        selected_pipeline = st.selectbox(
                            "Pipeline enregistré:",
                            pkl_files,
                            help="Sélectionnez un pipeline .pkl",
                            index=(
                                pkl_files.index("Pipeline_ML_PCA_Complete.pkl")
                                if "Pipeline_ML_PCA_Complete.pkl" in pkl_files
                                else 0
                            ),
                        )

                        st.success(f"✅ **{selected_pipeline}**")

                        load_button = st.button(
                            "🔍 Charger et Analyser", use_container_width=True
                        )

                    with col2:
                        st.markdown("### 📄 Détails du Pipeline")

                        if load_button:
                            pipeline_path = os.path.join(
                                save_dir_paths, selected_pipeline
                            )

                            try:
                                with st.spinner("Chargement du pipeline..."):
                                    loaded_pipeline = joblib.load(
                                        pipeline_path
                                    )

                                    # Activer le mode Streamlit sur tous les transformateurs (récursif pour nested pipelines)
                                    def enable_streamlit_recursive(
                                        pipeline_obj,
                                    ):
                                        """Active use_streamlit=True récursivement sur tous les transformateurs."""
                                        if isinstance(pipeline_obj, Pipeline):
                                            for (
                                                name,
                                                transformer,
                                            ) in pipeline_obj.steps:
                                                # Si c'est un nested pipeline, récurser
                                                if isinstance(
                                                    transformer, Pipeline
                                                ):
                                                    enable_streamlit_recursive(
                                                        transformer
                                                    )
                                                # Sinon, activer use_streamlit
                                                elif hasattr(
                                                    transformer,
                                                    "use_streamlit",
                                                ):
                                                    transformer.use_streamlit = (
                                                        True
                                                    )
                                        elif hasattr(
                                            pipeline_obj, "use_streamlit"
                                        ):
                                            pipeline_obj.use_streamlit = True

                                    enable_streamlit_recursive(loaded_pipeline)

                                    st.session_state.loaded_pipeline = (
                                        loaded_pipeline
                                    )
                                    st.session_state.pipeline_name = (
                                        selected_pipeline
                                    )

                                st.success("✅ Pipeline chargé avec succès!")

                                # Afficher les étapes
                                st.markdown("**Étapes du pipeline:**")
                                for i, (name, transformer) in enumerate(
                                    loaded_pipeline.steps, 1
                                ):
                                    st.code(
                                        f"{i}. {name}: {transformer.__class__.__name__}"
                                    )

                            except Exception as e:
                                st.error(f"❌ Erreur de chargement: {e}")
                                st.session_state.loaded_pipeline = None

                # Exécution du pipeline chargé
                if (
                    "loaded_pipeline" in st.session_state
                    and st.session_state.loaded_pipeline is not None
                ):
                    st.divider()

                    container_exec = st.container(border=True)
                    with container_exec:
                        st.markdown(
                            f"### 🚀 Exécution: **{st.session_state.pipeline_name}**"
                        )

                        col_exec1, col_exec2 = st.columns([1, 3])

                        with col_exec1:
                            exec_button = st.button(
                                "▶️ Exécuter Pipeline",
                                use_container_width=True,
                                type="primary",
                            )

                        with col_exec2:
                            if exec_button:
                                # Import du pipeline executor (direct, pas via __init__)
                                utils_path = os.path.join(
                                    project_root, "src", "utils"
                                )
                                if utils_path not in sys.path:
                                    sys.path.insert(0, utils_path)
                                from pipeline_executor import (
                                    StreamlitPipelineExecutor,
                                )

                                try:
                                    # Créer l'exécuteur de pipeline
                                    executor = StreamlitPipelineExecutor(
                                        st.session_state.loaded_pipeline
                                    )
                                    total_steps = executor.get_total_steps()

                                    # Barre de progression globale
                                    st.markdown(
                                        "### 📊 Progression du Pipeline"
                                    )
                                    overall_progress = st.progress(0)
                                    overall_status = st.empty()

                                    st.divider()
                                    st.markdown("### 🔄 Exécution des Étapes")

                                    # Exécuter étape par étape avec UI
                                    result = None
                                    for (
                                        step_idx,
                                        _step_name,
                                        intermediate_result,
                                    ) in executor.execute_with_ui(
                                        X=None,
                                        show_intermediate=False,
                                        show_step_progress=True,
                                    ):
                                        # Mettre à jour la progression globale
                                        progress = (step_idx + 1) / total_steps
                                        overall_progress.progress(progress)
                                        overall_status.text(
                                            f"Progression globale: {int(progress * 100)}% "
                                            f"({step_idx + 1}/{total_steps} étapes complétées)"
                                        )

                                        result = intermediate_result

                                    # Finalisation
                                    overall_progress.progress(1.0)
                                    overall_status.success(
                                        "✅ Toutes les étapes terminées!"
                                    )

                                    st.divider()

                                    # Affichage des résultats
                                    st.success(
                                        "✅ Pipeline exécuté avec succès!"
                                    )

                                    # Analyser le résultat
                                    if isinstance(result, pd.DataFrame):
                                        st.info(
                                            f"📊 Résultat: DataFrame ({result.shape[0]} lignes, {result.shape[1]} colonnes)"
                                        )

                                        with st.expander("Voir les données"):
                                            st.dataframe(result.head(10))

                                            # Statistiques
                                            if "label" in result.columns:
                                                st.markdown(
                                                    "**Distribution des labels:**"
                                                )
                                                label_counts = result[
                                                    "label"
                                                ].value_counts()
                                                st.bar_chart(label_counts)

                                    elif isinstance(result, np.ndarray):
                                        st.info(
                                            f"📊 Résultat: Numpy Array {result.shape}"
                                        )
                                        st.text(
                                            f"Min: {result.min():.4f} | Max: {result.max():.4f} | Mean: {result.mean():.4f}"
                                        )

                                    elif isinstance(result, dict):
                                        st.info(
                                            "📊 Résultat: Dictionnaire (splits)"
                                        )
                                        for key, value in result.items():
                                            if isinstance(value, tuple):
                                                st.text(
                                                    f"  - {key}: {len(value[0])} samples"
                                                )

                                    else:
                                        st.info(
                                            f"📊 Résultat: {type(result).__name__}"
                                        )

                                    # Sauvegarder dans session state
                                    st.session_state.pipeline_result = result

                                except Exception as e:
                                    st.error(f"❌ Erreur d'exécution: {e}")
                                    import traceback

                                    with st.expander("Voir le traceback"):
                                        st.code(traceback.format_exc())

            # ============================================================
            # MODE 2: CRÉER UN NOUVEAU PIPELINE
            # ============================================================
            else:
                container_create = st.container(border=True)
                with container_create:
                    st.markdown("### 🆕 Création de Pipeline Personnalisé")

                    # Configuration du pipeline
                    st.markdown("#### 1️⃣ Configuration générale")
                    col_config1, col_config2 = st.columns(2)

                    with col_config1:
                        pipeline_name = st.text_input(
                            "Nom du pipeline:",
                            value="custom_pipeline",
                            help="Nom du fichier .pkl",
                        )
                        img_size = st.select_slider(
                            "Taille des images:",
                            options=[32, 64, 96, 128, 224, 256],
                            value=128,
                        )

                    with col_config2:
                        use_masks = st.checkbox(
                            "Utiliser les masques", value=False
                        )
                        use_augmentation = st.checkbox(
                            "Augmentation de données", value=False
                        )

                    st.divider()

                    # Sélection des transformateurs
                    st.markdown("#### 2️⃣ Sélection des transformateurs")

                    col_trans1, col_trans2, col_trans3 = st.columns(3)

                    with col_trans1:
                        st.markdown("**Preprocessing**")
                        do_resize = st.checkbox("ImageResizer", value=True)
                        do_normalize = st.checkbox(
                            "ImageNormalizer", value=True
                        )
                        do_grayscale = st.checkbox(
                            "RGB → Grayscale", value=True
                        )

                    with col_trans2:
                        st.markdown("**Features**")
                        do_flatten = st.checkbox("ImageFlattener", value=False)
                        do_pca = st.checkbox("ImagePCA", value=False)
                        do_histogram = st.checkbox(
                            "ImageHistogram", value=False
                        )

                        if do_pca:
                            n_components = st.slider(
                                "Composantes PCA:", 10, 100, 50
                            )
                        if do_histogram:
                            n_bins = st.slider("Bins histogram:", 8, 64, 32)

                    with col_trans3:
                        st.markdown("**Utilities**")
                        do_split = st.checkbox("Train/Test Split", value=False)
                        do_save = st.checkbox("SaveTransformer", value=False)

                        if do_split:
                            test_size = st.slider(
                                "Test size:", 0.1, 0.4, 0.2, 0.05
                            )

                    st.divider()

                    # Construction du pipeline
                    st.markdown("#### 3️⃣ Pipeline à créer")

                    # Construire la liste des étapes
                    pipeline_steps = [
                        (
                            "loader",
                            ImagePathLoader(
                                root_dir=data_dir,
                                verbose=True,
                                use_streamlit=True,
                            ),
                        ),
                        (
                            "tuple_to_df",
                            TupleToDataFrame(verbose=True, use_streamlit=True),
                        ),
                        (
                            "analyzer",
                            ImageAnalyser(
                                load_images=True,
                                analyze_masks=use_masks,
                                verbose=True,
                                use_streamlit=True,
                            ),
                        ),
                    ]

                    if do_resize:
                        pipeline_steps.append(
                            (
                                "resizer",
                                ImageResizer(
                                    img_size=(img_size, img_size),
                                    verbose=True,
                                    use_streamlit=True,
                                ),
                            )
                        )

                    if do_normalize:
                        pipeline_steps.append(
                            (
                                "normalizer",
                                ImageNormalizer(
                                    verbose=True, use_streamlit=True
                                ),
                            )
                        )

                    if use_augmentation:
                        pipeline_steps.append(
                            (
                                "augmenter",
                                ImageAugmenter(
                                    flip_horizontal=True,
                                    rotation_range=15,
                                    brightness_range=0.2,
                                    probability=0.5,
                                    verbose=True,
                                    use_streamlit=True,
                                ),
                            )
                        )

                    if use_masks:
                        pipeline_steps.append(
                            (
                                "masker",
                                ImageMasker(verbose=True, use_streamlit=True),
                            )
                        )

                    if do_grayscale:
                        pipeline_steps.append(
                            (
                                "gray",
                                RGB_to_L(verbose=True, use_streamlit=True),
                            )
                        )

                    if do_flatten:
                        pipeline_steps.append(
                            (
                                "flattener",
                                ImageFlattener(
                                    verbose=True, use_streamlit=True
                                ),
                            )
                        )

                    if do_histogram:
                        pipeline_steps.append(
                            (
                                "histogram",
                                ImageHistogram(
                                    bins=n_bins if do_histogram else 32,
                                    verbose=True,
                                    use_streamlit=True,
                                ),
                            )
                        )

                    if do_pca and do_flatten:
                        pipeline_steps.append(
                            (
                                "pca",
                                ImagePCA(
                                    n_components=(
                                        n_components if do_pca else 50
                                    ),
                                    verbose=True,
                                    use_streamlit=True,
                                ),
                            )
                        )

                    if do_split:
                        pipeline_steps.append(
                            (
                                "splitter",
                                TrainTestSplitter(
                                    test_size=test_size if do_split else 0.2,
                                    random_state=42,
                                    verbose=True,
                                    use_streamlit=True,
                                ),
                            )
                        )

                    if do_save:
                        pipeline_steps.append(
                            (
                                "saver",
                                SaveTransformer(
                                    save_dir="outputs",
                                    prefix=pipeline_name,
                                    verbose=True,
                                    use_streamlit=True,
                                ),
                            )
                        )

                    # Afficher l'aperçu
                    st.code(
                        "\n".join(
                            [
                                f"{i+1}. {name}: {step.__class__.__name__}"
                                for i, (name, step) in enumerate(
                                    pipeline_steps
                                )
                            ]
                        )
                    )

                    # Boutons d'action
                    col_action1, col_action2 = st.columns(2)

                    with col_action1:
                        create_button = st.button(
                            "🔧 Créer le Pipeline",
                            use_container_width=True,
                            type="primary",
                        )

                    with col_action2:
                        if create_button:
                            try:
                                # Créer le pipeline
                                new_pipeline = Pipeline(pipeline_steps)

                                # Sauvegarder
                                pipeline_path = os.path.join(
                                    save_dir_paths, f"{pipeline_name}.pkl"
                                )
                                joblib.dump(new_pipeline, pipeline_path)

                                st.success(
                                    f"✅ Pipeline créé et sauvegardé: `{pipeline_name}.pkl`"
                                )
                                st.session_state.created_pipeline = (
                                    new_pipeline
                                )
                                st.session_state.created_pipeline_name = (
                                    pipeline_name
                                )

                            except Exception as e:
                                st.error(f"❌ Erreur de création: {e}")


if __name__ == "__main__":
    run()
