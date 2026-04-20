"""Fonctions de visualisation Plotly pour la page 02_donnees."""

# pylint: disable=import-error

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from _data_utils import overlay_mask_on_image  # noqa: E402


def plot_luminosity_distributions(df_metrics: pd.DataFrame):
    """Plot violin charts of luminosity and contrast distributions by class."""
    fig_lum = px.violin(
        df_metrics,
        x="class",
        y="lum",
        box=True,
        points="all",
        labels={"lum": "Luminosité moyenne", "class": "Classe"},
        title="Distribution de la luminosité par classe",
        color="class",
    )
    st.plotly_chart(fig_lum, width="stretch")
    fig_std = px.violin(
        df_metrics,
        x="class",
        y="std",
        box=True,
        points="all",
        labels={"std": "Contraste (écart-type)", "class": "Classe"},
        title="Distribution du contraste par classe",
        color="class",
    )
    st.plotly_chart(fig_std, width="stretch")


def plot_mask_coverage(by_class: dict, classes: list[str]):
    """Plot a box chart of mask coverage percentages per class."""
    long_data = [
        {"class": cls, "mask_cov": cov}
        for cls in classes
        for cov in by_class[cls].get("mask_coverages", [])
    ]
    if not long_data:
        st.info("Aucune donnée de masque disponible.")
        return
    df_masks = pd.DataFrame(long_data)
    fig = px.box(
        df_masks,
        x="class",
        y="mask_cov",
        labels={"mask_cov": "Couverture (%)", "class": "Classe"},
        title="Distribution de la couverture des masques par classe",
        color="class",
    )
    st.plotly_chart(fig, width="stretch")


def show_mask_overlays(per_image: list[dict], max_examples: int = 3):
    """Display side-by-side mask overlay images for a sample of entries."""
    st.markdown("### Exemples de masques superposés")
    mask_examples = [e for e in per_image if e.get("mask")]
    if not mask_examples:
        st.info("Aucun masque détecté dans le dataset.")
        return
    examples = mask_examples[:max_examples]
    cols = st.columns(len(examples))
    for i, entry in enumerate(examples):
        with cols[i]:
            try:
                img_path = Path(entry["path"])
                mask_path = Path(entry["mask"])
                overlay = overlay_mask_on_image(img_path, mask_path, alpha=0.4)
                overlay.thumbnail((320, 320))
                st.image(overlay, caption=img_path.name)
                cov = entry.get("mask_coverage")
                if cov is not None:
                    st.metric("Couverture", f"{cov:.1f}%")
            except Exception as e:  # pylint: disable=broad-exception-caught
                st.error(f"Erreur : {e}")
