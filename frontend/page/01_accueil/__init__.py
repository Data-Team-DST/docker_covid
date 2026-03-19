"""Page 01 — Accueil : contexte COVID-19 et objectifs SMART."""

# pylint: disable=line-too-long,wrong-import-position,invalid-name,import-error

import sys
from pathlib import Path

import streamlit as st
from streamlit_extras.colored_header import colored_header

_HERE = Path(__file__).parent
if str(_HERE) in sys.path:
    sys.path.remove(str(_HERE))
sys.path.insert(0, str(_HERE))
for _k in ["_context", "_objectives"]:
    sys.modules.pop(_k, None)

from _context import render_context  # noqa: E402
from _objectives import render_objectives  # noqa: E402

_CSS = """
<style>
:root{ --bg:#0f1115; --card:#131416; --muted:#9aa1a6; --accent:#4fc3f7; }
body, .stApp {
  background: var(--bg); color: #e6eef6;
  font-family: "Inter", sans-serif;
}
.project-hero {
  background: linear-gradient(
    135deg, rgba(10,20,40,0.85), rgba(6,10,20,0.75));
  padding: 18px; border-radius: 12px;
  box-shadow: 0 6px 18px rgba(0,0,0,0.5); color: #e6eef6;
}
.small-note { font-size:12px; color:#98a1b3; }
</style>
"""


def run():
    """Point d'entrée de la page d'accueil."""
    st.markdown(_CSS, unsafe_allow_html=True)
    try:
        colored_header(
            label=("Analyse de radiographies pulmonaires" " — Classification COVID-19"),
            description=(
                "Projet réalisé par Cirine B., Lena B.," " Steven M., Rafael C."
            ),
            color_name="blue-70",
        )
    except Exception:  # pylint: disable=broad-exception-caught
        st.markdown(
            "<h2>Analyse de radiographies pulmonaires</h2>",
            unsafe_allow_html=True,
        )
    st.divider()
    render_context()
    render_objectives()


if __name__ == "__main__":
    run()
