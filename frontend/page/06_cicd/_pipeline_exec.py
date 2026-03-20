"""Pipeline Sklearn — exécution et affichage des résultats."""

import os
import sys

import numpy as np
import pandas as pd
import streamlit as st


def render_exec():
    """Exécute le pipeline chargé en session et affiche les résultats."""
    st.divider()
    container = st.container(border=True)
    with container:
        st.markdown(f"### 🚀 Exécution: **{st.session_state.pipeline_name}**")
        col1, col2 = st.columns([1, 3])
        with col1:
            exec_btn = st.button(
                "▶️ Exécuter Pipeline", use_container_width=True, type="primary"
            )
        with col2:
            if exec_btn:
                _run_pipeline()


def _run_pipeline():
    """Lance l'exécution étape par étape et affiche la progression."""
    project_root = st.session_state.get("project_root", "")
    utils_path = os.path.join(project_root, "src", "utils")
    if utils_path not in sys.path:
        sys.path.insert(0, utils_path)

    try:
        from pipeline_executor import StreamlitPipelineExecutor  # noqa: PLC0415

        executor = StreamlitPipelineExecutor(st.session_state.loaded_pipeline)
        total = executor.get_total_steps()
        progress_bar = st.progress(0)
        status = st.empty()
        st.divider()
        st.markdown("### 🔄 Exécution des Étapes")

        result = None
        for step_idx, _step_name, intermediate in executor.execute_with_ui(
            X=None, show_intermediate=False, show_step_progress=True
        ):
            pct = (step_idx + 1) / total
            progress_bar.progress(pct)
            status.text(f"Progression: {int(pct * 100)}% ({step_idx + 1}/{total})")
            result = intermediate

        progress_bar.progress(1.0)
        status.success("✅ Toutes les étapes terminées!")
        st.divider()
        _display_result(result)
        st.session_state.pipeline_result = result

    except Exception as e:  # pylint: disable=broad-exception-caught
        import traceback  # noqa: PLC0415

        st.error(f"❌ Erreur d'exécution: {e}")
        with st.expander("Voir le traceback"):
            st.code(traceback.format_exc())


def _display_result(result):
    """Affiche le résultat du pipeline selon son type."""
    st.success("✅ Pipeline exécuté avec succès!")
    if isinstance(result, pd.DataFrame):
        rows, cols = result.shape[0], result.shape[1]
        st.info(f"📊 DataFrame ({rows} lignes, {cols} colonnes)")
        with st.expander("Voir les données"):
            st.dataframe(result.head(10))
            if "label" in result.columns:
                st.markdown("**Distribution des labels:**")
                st.bar_chart(result["label"].value_counts())
    elif isinstance(result, np.ndarray):
        st.info(f"📊 Numpy Array {result.shape}")
        mn, mx, mean = result.min(), result.max(), result.mean()
        st.text(f"Min: {mn:.4f} | Max: {mx:.4f} | Mean: {mean:.4f}")
    elif isinstance(result, dict):
        st.info("📊 Dictionnaire (splits)")
        for key, value in result.items():
            if isinstance(value, tuple):
                st.text(f"  - {key}: {len(value[0])} samples")
    else:
        st.info(f"📊 Résultat: {type(result).__name__}")
