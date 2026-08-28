"""Demonstration Flask — DS_COVID MLOps — facade demo produit (contexte, prédicteur, modèles)."""
import os

import requests
from flask import Flask, redirect, render_template, request

app = Flask(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:5050")
API_KEY = os.getenv("API_KEY", "")


@app.context_processor
def inject_dashboard_url():
    """Rend dashboard_url disponible dans tous les templates (lien croisé vers dashboard/)."""
    return {"dashboard_url": DASHBOARD_URL}


@app.route("/")
def index():
    """Pas de page d'accueil dédiée — redirige vers la première page de la démo."""
    return redirect("/contexte")


@app.route("/contexte")
def contexte():
    return render_template("contexte.html")


@app.route("/conclusion")
def conclusion():
    """Conclusion critique et perspectives — condensé depuis
    frontend/page/07_conclusion_critique_perspective.py (chantier point 15)."""
    return render_template("conclusion.html")


@app.route("/preprocessing")
def preprocessing():
    """Environnements/masking/déséquilibre/augmentation — condensé depuis
    frontend/page/03_preprocessing (chantier point 15)."""
    return render_template("preprocessing.html")


@app.route("/predict", methods=["GET", "POST"])
def predict():
    if request.method == "GET":
        return render_template("predict.html", result=None, error=None)

    file = request.files.get("file")
    if not file or not file.filename:
        return render_template(
            "predict.html", result=None, error="Aucun fichier sélectionné."
        )

    try:
        r = requests.post(
            f"{BACKEND_URL}/api/v1/predict",
            files={"file": (file.filename, file.stream, file.mimetype)},
            headers={"X-API-Key": API_KEY},
            timeout=30,
        )
    except requests.exceptions.ConnectionError:
        return render_template(
            "predict.html",
            result=None,
            error=f"Backend inaccessible ({BACKEND_URL}) — lancer : make start",
        )

    if r.status_code != 200:
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        return render_template(
            "predict.html", result=None, error=f"Erreur {r.status_code} : {detail}"
        )

    return render_template("predict.html", result=r.json(), error=None)


@app.route("/modeles")
def model_status():
    """Provenance des modèles chargés (MLflow Registry vs fichier local, cf. US
    chantier infra #17) — interroge /health du backend, qui interroge lui-même
    celui du segmentation-service."""
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=5)
        r.raise_for_status()
        health = r.json()
        error = None
    except requests.exceptions.RequestException as e:
        health = None
        error = f"Backend inaccessible ({BACKEND_URL}) — {e}"

    return render_template("model_status.html", health=health, error=error)


if __name__ == "__main__":
    port = int(os.getenv("DEMONSTRATION_PORT", "5051"))
    app.run(host="0.0.0.0", port=port, debug=False)
