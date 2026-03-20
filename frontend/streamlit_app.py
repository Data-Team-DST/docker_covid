# streamlit_app.py — Point d'entrée DS_COVID
# pylint: disable=wrong-import-position

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from _nav import BADGES_EMOJIS, GRADIENTS, NAV_LABELS, PAGE_FILENAMES  # noqa: E402
from _styles import DARK_THEME_CSS  # noqa: E402
from page._loader import load_pages  # noqa: E402

st.set_page_config(page_title="Projet DS COVID", layout="wide", page_icon="🧪")

_PAGE_DIR = Path(__file__).parent / "page"
_loaded_pages, _import_errors = load_pages(_PAGE_DIR, PAGE_FILENAMES)

if _import_errors:
    for fname, err in _import_errors:
        st.error(f"Impossible d'importer `{fname}` — {err}")
    st.stop()

st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)

_tabs = st.tabs([f"{label} {BADGES_EMOJIS[i]}" for i, label in enumerate(NAV_LABELS)])

for idx, tab in enumerate(_tabs):
    fname, mod = _loaded_pages[idx]
    with tab:
        gradient = GRADIENTS[idx % len(GRADIENTS)]
        st.markdown(
            f"<div class='hero-header' style='background:{gradient}'>"
            f"{NAV_LABELS[idx]}</div>",
            unsafe_allow_html=True,
        )
        try:
            mod.run()
            st.markdown(
                f"<div style='font-size:11px;color:#98a1b3;margin-top:6px;'>"
                f"Page chargée : `{fname}` — run() OK.</div>",
                unsafe_allow_html=True,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            st.error(f"Erreur `run()` dans `{fname}` : {e}")
            st.markdown(
                "<div style='font-size:12px;color:#d88;'>"
                "Vérifiez la fonction run() dans le module.</div>",
                unsafe_allow_html=True,
            )
