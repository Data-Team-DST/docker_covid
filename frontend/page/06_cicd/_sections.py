"""Sections CI/CD — contenu markdown des 7 parties."""

import streamlit as st


def render_cicd_content():
    """Affiche les 7 sections de présentation du pipeline CI/CD."""
    container = st.container(border=True)
    with container:
        st.markdown("## 1. Pourquoi un pipeline CI/CD ?")
        st.markdown(
            "Même sans déploiement industriel, nous avons mis en place "
            "des pratiques de **qualité, reproductibilité et "
            "maintenabilité**. L'objectif est d'éviter "
            "le code fragile, les régressions et la dette technique."
        )
        st.divider()

        st.markdown("## 2. Pipeline CI")
        st.markdown("Exécuté automatiquement via GitHub Actions à chaque push/PR :")
        st.markdown(
            "- Linting Python avec pylint (score ≥ 8)\n"
            "- Tests unitaires avec pytest\n"
            "- Rapports de couverture\n"
            "- Analyse statique SonarCloud"
        )
        st.divider()

        st.markdown("## 3. Philosophie qualité & tests")
        st.markdown(
            "Approche pragmatique : priorité à la lisibilité, "
            "robustesse et détection précoce des régressions. "
            "Tests ciblés sur les composants critiques, "
            "couverture volontairement modeste mais contrôlée."
        )
        st.divider()

        st.markdown("## 4. Artefacts produits")
        st.markdown(
            "- Rapports pytest (coverage.xml)\n"
            "- Analyses SonarCloud\n"
            "- Logs GitHub Actions\n"
            "- Historique des exécutions CI"
        )
        st.divider()

        st.markdown("## 5. Limites assumées")
        st.markdown(
            "Certains éléments classiques ne sont pas implémentés "
            "par choix pédagogique :\n"
            "- Pas de build Docker\n"
            "- Pas de CD / déploiement continu\n"
            "- Pas d'orchestration Kubernetes\n"
            "- Pas de monitoring temps réel\n\n"
            "→ Cohérent avec le périmètre académique "
            "et les ressources disponibles."
        )
        st.divider()

        st.markdown("## 6. Perspectives")
        st.markdown(
            "- Introduction progressive de Docker\n"
            "- Séparation CI / CD\n"
            "- Déploiement contrôlé en test\n"
            "- Monitoring basique performances/dérives"
        )
        st.divider()

        st.markdown("## 7. Positionnement final")
        st.markdown(
            "- Pipeline CI réel, orienté qualité\n"
            "- Au-delà des exigences minimales\n"
            "- Adapté à un projet académique avancé\n"
            "- Base crédible pour industrialisation future"
        )
        st.divider()
