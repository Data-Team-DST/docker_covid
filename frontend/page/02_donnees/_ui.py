"""Sections UI de la page 02_donnees : échantillon, scan, galerie
anomalies."""

# code-smell: max-lines=150 reason="3 sections UI cohésives de la page données"
# pylint: disable=wrong-import-position,import-error,too-many-locals

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image
from streamlit_extras.colored_header import colored_header

_HERE = Path(__file__).parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _config import THUMBNAIL_MAX  # noqa: E402
from _data_utils import (  # noqa: E402
    compute_image_metrics,
    mask_coverage,
    run_full_dataset_scan,
    sample_images_from_class,
)
from _visualizations import (  # noqa: E402
    plot_luminosity_distributions,
    plot_mask_coverage,
    show_mask_overlays,
)


def render_quick_sample(dataset_root: Path, classes: list):
    """Sélection et affichage d'un échantillon d'images."""
    colored_header(
        "Échantillonnage rapide",
        "Visualisation d'un petit échantillon",
        color_name="violet-70",
    )
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        choice = st.selectbox("Choisir une classe :", options=classes)
    with col2:
        n = st.number_input("Nombre d'images :", 1, 5, 5)
    with col3:
        if st.button("Nouvel échantillon"):
            st.session_state.pop("viz_sample", None)

    sample_key = f"{choice}__{n}"
    cached = st.session_state.get("viz_sample", {})
    if cached.get("key") != sample_key:
        imgs = sample_images_from_class(dataset_root, choice, n)
        st.session_state["viz_sample"] = {
            "key": sample_key,
            "images": [str(p) for p in imgs],
        }

    img_paths = [Path(p) for p in st.session_state["viz_sample"]["images"]]
    if not img_paths:
        st.info("Aucune image disponible.")
        return
    img_names = [p.name for p in img_paths]
    selected = st.selectbox("Choisir une image :", options=img_names)
    img_path = img_paths[img_names.index(selected)]
    mask_path = dataset_root / choice / "masks" / img_path.name
    try:
        img = Image.open(img_path).convert("RGB")
        img.thumbnail(THUMBNAIL_MAX)
        col_img, col_mask = st.columns(2)
        with col_img:
            st.markdown("**Image**")
            st.image(img, caption=img_path.name)
        with col_mask:
            st.markdown("**Masque**")
            if mask_path.exists():
                m = Image.open(mask_path).convert("L")
                m.thumbnail(THUMBNAIL_MAX)
                st.image(m, caption=mask_path.name)
            else:
                st.info("Aucun masque pour cette image.")
        metrics = compute_image_metrics(img)
        mask_cov = mask_coverage(mask_path) if mask_path.exists() else None
        ca, cb, cc, cd = st.columns(4)
        ca.metric("Luminosité", f"{metrics['luminosity_mean']:.1f}")
        cb.metric("Contraste", f"{metrics['contrast_std']:.1f}")
        cc.metric("Entropie", f"{metrics['entropy']:.2f}")
        cd.metric(
            "Couverture masque",
            f"{mask_cov:.1f}%" if mask_cov else "N/A",
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        st.error(f"Erreur : {e}")


def render_full_scan(dataset_root: Path, classes: list):
    """Lancement et affichage du scan complet du dataset."""
    st.divider()
    colored_header(
        "Analyse complète du dataset",
        "Scan sur l'ensemble des données",
        color_name="violet-70",
    )
    if st.button("Lancer le scan complet", type="primary"):
        st.session_state.pop("last_scan", None)
    if "last_scan" not in st.session_state:
        with st.spinner("Scan en cours…"):
            st.session_state["last_scan"] = run_full_dataset_scan(
                dataset_root, classes, True
            )
    scan_data = st.session_state["last_scan"]
    if not scan_data or not scan_data.get("per_image"):
        st.warning("Scan vide ou incomplet.")
        return
    st.metric("Images analysées", f"{len(scan_data['per_image']):,}")
    rows = [
        {
            "class": e["class"],
            "lum": e["metrics"]["luminosity_mean"],
            "std": e["metrics"]["contrast_std"],
            "entropy": e["metrics"]["entropy"],
        }
        for e in scan_data["per_image"]
    ]
    plot_luminosity_distributions(pd.DataFrame(rows))
    show_mask_overlays(scan_data["per_image"], max_examples=3)
    plot_mask_coverage(scan_data["by_class"], classes)


def render_anomaly_gallery():
    """Galerie d'outliers radiographiques."""
    colored_header(
        "Galerie d'outliers radiographiques",
        "Artefacts observés dans les radiographies",
        color_name="violet-70",
    )
    anomalies_dir = Path(__file__).parent.parent / "images" / "anomalies_cxr"
    if not anomalies_dir.exists():
        st.warning("Le dossier anomalies_cxr n'existe pas.")
        return
    anomaly_images = sorted(
        [f for f in anomalies_dir.iterdir() if f.suffix.lower() == ".png"]
    )
    if not anomaly_images:
        st.info("Le dossier anomalies_cxr est vide.")
        return
    names = [img.name for img in anomaly_images]
    selected = st.selectbox("Choisir une anomalie :", options=names)
    img = Image.open(anomaly_images[names.index(selected)]).convert("RGB")
    st.image(img, caption=selected)
