import os
import streamlit as st

st.set_page_config(page_title="COVID X-Ray Detection")

st.title("COVID X-Ray Detection")

st.write("Interface de test pour la détection COVID à partir de radiographies.")

st.write("MLflow URI :", os.getenv("MLFLOW_TRACKING_URI"))

uploaded_file = st.file_uploader(
    "Charger une radiographie",
    type=["png", "jpg", "jpeg"]
)

if uploaded_file is not None:
    st.image(uploaded_file)
    st.success("Image chargée")

st.info("Prochaine étape : connecter le modèle TensorFlow.")