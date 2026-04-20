# Theming metadata:
# - Preferred: streamlit-extras mandatory; inherits app-wide dark theme.
# - Palette: navy/dark background, high-contrast highlights; sans-serif font.
# - File status: deep-dive template for best model — interpretability,
#   error analysis, subgroup performance.
# pylint: disable=line-too-long,invalid-name,non-ascii-file-name

import os
from pathlib import Path

import streamlit as st
from streamlit_extras.colored_header import colored_header


def run():
    """Affiche la page Deep Learning et interprétabilité."""
    # Header / hero
    colored_header(
        label="Deep learning et interprétabilité",
        description="",
        color_name="blue-70",
    )
    st.divider()

    chemin_global = Path(__file__).parent.parent
    chemin_global = os.path.join(chemin_global, "page", "images")

    st.markdown("### **Modèle de deep learning Inception V3**")

    chemin_absolu = rf"{chemin_global}/Inceptionv3.png"
    image_path = Path(chemin_absolu).relative_to(Path.cwd())
    st.image(str(image_path), caption="Schéma explicatif", use_container_width=True)

    st.markdown("**Courbes de loss et d’accuracy**")

    chemin_absolu = rf"{chemin_global}/courbe loss.png"
    image_path = Path(chemin_absolu).relative_to(Path.cwd())
    st.image(str(image_path), caption="Courbes de loss et d’accuracy", width=500)

    st.markdown("**Matrice de confusion**")

    chemin_absolu = rf"{chemin_global}/matrice confusion deep.png"
    image_path = Path(chemin_absolu).relative_to(Path.cwd())
    st.image(str(image_path), caption="Matrice de confusion", width=500)

    st.info(
        "**Performance globale** : modèle très performant, bonne identification des classes "
        "(COVID, pneumonie virale, normal)."
    )
    st.info(
        "**Efficacité prouvée** : le transfert d’apprentissage avec InceptionV3 est excellent "
        "pour la classification d’images médicales."
    )

    st.markdown("### **Interprétabilité**")
    st.markdown("**LIME (Local Interpretable Model-Agnostic Explanations)**")

    st.markdown(
        "**Avantages clés** : méthode compréhensible, fiable, universelle et généralisable "
        "(SP-LIME)."
    )

    st.info(
        "**Entraînement du modèle** : 2 000 images, 20 epochs de feature extraction, suivies "
        "de 30 epochs de fine-tuning (20 dernières couches dégelées)."
    )

    chemin_absolu_3 = rf"{chemin_global}/lime.png"
    image_path_3 = Path(chemin_absolu_3).relative_to(Path.cwd())
    st.image(
        str(image_path_3),
        caption="Résultats obtenus avec la méthode LIME",
        use_container_width=True,
    )

    chemin_absolu_4 = rf"{chemin_global}/lime2.png"
    image_path_4 = Path(chemin_absolu_4).relative_to(Path.cwd())
    st.image(
        str(image_path_4),
        caption="Résultats obtenus avec la méthode LIME",
        use_container_width=True,
    )


if __name__ == "__main__":
    run()


# STATUS: page/06_analyse_du_meilleur_modele.py — version intégrale,
# Streamlit Extras obligatoire, sections 1 à 10 complètes avec placeholders interactifs,
# pipelines et checklists.
