"""Pipeline Sklearn — MODE 1 : charger un pipeline existant."""

# pylint: disable=import-error
import os

import streamlit as st


def render_load_mode(save_dir: str):
    """Interface de chargement et exécution d'un pipeline existant (.pkl)."""
    # pylint: disable=too-many-locals
    import joblib  # noqa: PLC0415
    from sklearn.pipeline import Pipeline  # noqa: PLC0415

    # Import Transformateurs AVANT joblib (requis pour unpickling)
    # pylint: disable=unused-import
    from src.features.St_Pipeline.Transformateurs import (  # noqa: PLC0415, F401
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

    pkl_files = [f for f in os.listdir(save_dir) if f.endswith(".pkl")]
    if not pkl_files:
        st.warning(f"⚠️ Aucun pipeline trouvé dans `{save_dir}`")
        st.info("💡 Créez un nouveau pipeline ou utilisez le notebook.")
        return

    container = st.container(border=True)
    with container:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("### 📋 Sélection")
            default = (
                pkl_files.index("Pipeline_ML_PCA_Complete.pkl")
                if "Pipeline_ML_PCA_Complete.pkl" in pkl_files
                else 0
            )
            selected = st.selectbox("Pipeline enregistré:", pkl_files, index=default)
            st.success(f"✅ **{selected}**")
            load_btn = st.button("🔍 Charger et Analyser", use_container_width=True)

        with col2:
            st.markdown("### 📄 Détails du Pipeline")
            if load_btn:
                _load_and_display(save_dir, selected, joblib, Pipeline)

    _render_exec_section()


def _load_and_display(save_dir: str, selected: str, joblib, pipeline_cls):
    """Charge un pipeline .pkl et affiche ses étapes."""
    try:
        with st.spinner("Chargement du pipeline..."):
            pipeline = joblib.load(os.path.join(save_dir, selected))
            _enable_streamlit_recursive(pipeline, pipeline_cls)
            st.session_state.loaded_pipeline = pipeline
            st.session_state.pipeline_name = selected
        st.success("✅ Pipeline chargé avec succès!")
        st.markdown("**Étapes du pipeline:**")
        for i, (name, transformer) in enumerate(pipeline.steps, 1):
            st.code(f"{i}. {name}: {transformer.__class__.__name__}")
    except Exception as e:  # pylint: disable=broad-exception-caught
        st.error(f"❌ Erreur de chargement: {e}")
        st.session_state.loaded_pipeline = None


def _enable_streamlit_recursive(pipeline_obj, pipeline_cls):
    """Active use_streamlit=True récursivement sur tous les transformateurs."""
    if isinstance(pipeline_obj, pipeline_cls):
        for _, transformer in pipeline_obj.steps:
            if isinstance(transformer, pipeline_cls):
                _enable_streamlit_recursive(transformer, pipeline_cls)
            elif hasattr(transformer, "use_streamlit"):
                transformer.use_streamlit = True
    elif hasattr(pipeline_obj, "use_streamlit"):
        pipeline_obj.use_streamlit = True


def _render_exec_section():
    """Affiche la section d'exécution si un pipeline est chargé."""
    if not (
        "loaded_pipeline" in st.session_state
        and st.session_state.loaded_pipeline is not None
    ):
        return

    from _pipeline_exec import render_exec  # noqa: PLC0415

    render_exec()
