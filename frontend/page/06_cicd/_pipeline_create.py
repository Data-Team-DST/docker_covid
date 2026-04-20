"""Pipeline Sklearn — MODE 2 : créer un nouveau pipeline."""

# code-smell: max-lines=105 reason="Formulaire UI cohésif"
# pylint: disable=import-error

import os

import streamlit as st
from sklearn.pipeline import Pipeline


def render_create_mode(data_dir: str, save_dir: str):
    """Interface de création et sauvegarde d'un pipeline personnalisé."""
    container = st.container(border=True)
    with container:
        st.markdown("### 🆕 Création de Pipeline Personnalisé")
        cfg = _render_config_ui()
        pipeline_steps = _build_steps_from_ui(cfg, data_dir)
        _render_preview_and_save(pipeline_steps, cfg["pipeline_name"], save_dir)


def _render_config_ui() -> dict:  # pylint: disable=too-many-locals
    """Affiche les contrôles de configuration et retourne le dict de config."""
    st.markdown("#### 1️⃣ Configuration générale")
    col1, col2 = st.columns(2)
    with col1:
        pipeline_name = st.text_input("Nom du pipeline:", value="custom_pipeline")
        img_size = st.select_slider(
            "Taille des images:", options=[32, 64, 96, 128, 224, 256], value=128
        )
    with col2:
        use_masks = st.checkbox("Utiliser les masques", value=False)
        use_augmentation = st.checkbox("Augmentation de données", value=False)
    st.divider()

    st.markdown("#### 2️⃣ Sélection des transformateurs")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Preprocessing**")
        do_resize = st.checkbox("ImageResizer", value=True)
        do_normalize = st.checkbox("ImageNormalizer", value=True)
        do_grayscale = st.checkbox("RGB → Grayscale", value=True)
    with c2:
        st.markdown("**Features**")
        do_flatten = st.checkbox("ImageFlattener", value=False)
        do_pca = st.checkbox("ImagePCA", value=False)
        do_histogram = st.checkbox("ImageHistogram", value=False)
        n_components = st.slider("Composantes PCA:", 10, 100, 50) if do_pca else 50
        n_bins = st.slider("Bins histogram:", 8, 64, 32) if do_histogram else 32
    with c3:
        st.markdown("**Utilities**")
        do_split = st.checkbox("Train/Test Split", value=False)
        do_save = st.checkbox("SaveTransformer", value=False)
        test_size = st.slider("Test size:", 0.1, 0.4, 0.2, 0.05) if do_split else 0.2

    return {
        "pipeline_name": pipeline_name,
        "img_size": img_size,
        "use_masks": use_masks,
        "use_augmentation": use_augmentation,
        "do_resize": do_resize,
        "do_normalize": do_normalize,
        "do_grayscale": do_grayscale,
        "do_flatten": do_flatten,
        "do_pca": do_pca,
        "do_histogram": do_histogram,
        "do_split": do_split,
        "do_save": do_save,
        "n_components": n_components,
        "n_bins": n_bins,
        "test_size": test_size,
    }


def _build_steps_from_ui(cfg: dict, data_dir: str) -> list:
    """Délègue la construction des étapes à _pipeline_steps."""
    from _pipeline_steps import build_pipeline_steps  # noqa: PLC0415

    return build_pipeline_steps(cfg, data_dir)


def _render_preview_and_save(steps: list, name: str, save_dir: str):
    """Affiche l'aperçu du pipeline et le bouton de sauvegarde."""
    st.divider()
    st.markdown("#### 3️⃣ Pipeline à créer")
    st.code(
        "\n".join(
            f"{i+1}. {n}: {s.__class__.__name__}" for i, (n, s) in enumerate(steps)
        )
    )

    col1, col2 = st.columns(2)
    with col1:
        create_btn = st.button(
            "🔧 Créer le Pipeline", use_container_width=True, type="primary"
        )
    with col2:
        if create_btn:
            try:
                pipeline = Pipeline(steps)
                path = os.path.join(save_dir, f"{name}.pkl")
                import joblib  # noqa: PLC0415

                joblib.dump(pipeline, path)
                st.success(f"✅ Pipeline créé et sauvegardé: `{name}.pkl`")
                st.session_state.created_pipeline = pipeline
            except Exception as e:  # pylint: disable=broad-exception-caught
                st.error(f"❌ Erreur de création: {e}")
