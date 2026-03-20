"""Page 02 — Présentation des données COVID-19."""

# pylint: disable=invalid-name,wrong-import-position,import-error

import sys
from pathlib import Path

import streamlit as st
from streamlit_extras.colored_header import colored_header

_HERE = Path(__file__).parent
if str(_HERE) in sys.path:
    sys.path.remove(str(_HERE))
sys.path.insert(0, str(_HERE))
for _k in ["_config", "_data_utils", "_ui", "_visualizations"]:
    sys.modules.pop(_k, None)

from _config import (  # noqa: E402
    CSS,
    DEFAULT_CLASS_COUNTS,
    DEFAULT_TOTAL,
    KAGGLE_SLUG,
)
from _data_utils import (  # noqa: E402
    get_kaggle_dataset_path,
    looks_like_images,
)
from _ui import (  # noqa: E402
    render_anomaly_gallery,
    render_full_scan,
    render_quick_sample,
)


def _render_section(title: str, body: str):
    st.markdown(
        f"<div class='section-card'>"
        f"<div class='label'>{title}</div>"
        f"<div>{body}</div></div>",
        unsafe_allow_html=True,
    )


def run():
    """Point d'entrée de la page données."""
    st.markdown(CSS, unsafe_allow_html=True)
    try:
        colored_header(
            label="Présentation des données",
            description="",
            color_name="blue-70",
        )
    except Exception:  # pylint: disable=broad-exception-caught
        st.markdown("### Présentation des données")
    st.divider()

    _render_section("Inventaire et volumétrie", f"Dataset : {KAGGLE_SLUG}")
    table_md = "| Classe | Images | Masques |\n|---:|---:|---:|\n"
    for k, v in DEFAULT_CLASS_COUNTS.items():
        table_md += f"| {k} | {v} | {v} |\n"
    table_md += f"| **Total** | **{DEFAULT_TOTAL}** | **{DEFAULT_TOTAL}** |"
    st.markdown(table_md)
    st.markdown(
        "**Remarque cruciale** : la distribution présente un déséquilibre notable."
    )
    _render_section(
        "Caractéristiques graphiques",
        "<ul><li>Format : PNG</li>"
        "<li>Résolution : 299×299 px (images) / 256×256 px (masques)</li>"
        "<li>Masques : binaires, alignés avec les images</li></ul>",
    )

    st.markdown("## Import et aperçu rapide (Kaggle)")
    dataset_root = get_kaggle_dataset_path(KAGGLE_SLUG)
    if not dataset_root:
        st.error("Dataset Kaggle introuvable ou téléchargement échoué.")
        return
    dataset_root = dataset_root / "COVID-19_Radiography_Dataset"
    st.write(f"Racine détectée : `{dataset_root}`")
    classes = sorted([p.name for p in dataset_root.iterdir() if looks_like_images(p)])
    if not classes:
        st.error("Aucune classe détectée.")
        return
    st.write(f"Classes détectées : {classes}")
    st.session_state["dataset_root"] = str(dataset_root)
    st.session_state["classes"] = classes

    render_quick_sample(dataset_root, classes)
    render_full_scan(dataset_root, classes)
    render_anomaly_gallery()


if __name__ == "__main__":
    run()
