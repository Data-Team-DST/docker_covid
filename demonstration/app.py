"""Demonstration Flask — DS_COVID MLOps — facade demo produit (contexte, prédicteur, modèles)."""
import base64
import os
from pathlib import Path

import requests
from flask import Flask, render_template, request, send_file

app = Flask(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:5050")
API_KEY = os.getenv("API_KEY", "")

# Rapport de dérive Evidently — versionné DVC (outputs/drift/report.html.dvc), récupéré via
# `dvc pull` avant la démo. Chemin absolu : app.py tourne avec cwd=demonstration/ (make demonstration).
DRIFT_REPORT_PATH = Path(__file__).resolve().parent.parent / "outputs" / "drift" / "report.html"

# Liens outils de monitoring — mêmes ports par défaut que infrastructure/docker-compose.yml
# (services sous profil "monitoring" pour prometheus/grafana : make monitoring-start).
MLFLOW_URL = os.getenv("MLFLOW_URL", "http://localhost:5000")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
DAGSHUB_URL = os.getenv("DAGSHUB_URL", "https://dagshub.com/DST_Data_Team/docker_covid")

# Ordre de présentation (soutenance) — pilote la nav séquentielle Précédent/Suivant.
PAGE_ORDER = [
    ("/", "Sommaire"),
    ("/contexte", "Contexte DS"),
    ("/preprocessing", "Préprocessing"),
    ("/predict", "Prédicteur"),
    ("/architecture", "Architecture"),
    ("/modeles", "Modèles"),
    ("/monitoring", "Monitoring"),
    ("/conclusion", "Conclusion"),
]


@app.context_processor
def inject_dashboard_url():
    """Rend dashboard_url disponible dans tous les templates (lien croisé vers dashboard/)."""
    return {"dashboard_url": DASHBOARD_URL}


def nav_context(current_path: str) -> dict:
    """Précédent/suivant dans PAGE_ORDER, pour la nav séquentielle Précédent/Suivant."""
    idx = next(i for i, (path, _) in enumerate(PAGE_ORDER) if path == current_path)
    return {
        "prev_page": PAGE_ORDER[idx - 1] if idx > 0 else None,
        "next_page": PAGE_ORDER[idx + 1] if idx < len(PAGE_ORDER) - 1 else None,
    }


@app.route("/")
def sommaire():
    """Écran d'ouverture de la présentation — sommaire visuel des 5 étapes."""
    return render_template("sommaire.html", **nav_context("/"))


@app.route("/contexte")
def contexte():
    return render_template("contexte.html", **nav_context("/contexte"))


@app.route("/conclusion")
def conclusion():
    """Conclusion critique et perspectives — condensé depuis
    frontend/page/07_conclusion_critique_perspective.py (chantier point 15)."""
    return render_template("conclusion.html", **nav_context("/conclusion"))


@app.route("/preprocessing")
def preprocessing():
    """Environnements/masking/déséquilibre/augmentation — condensé depuis
    frontend/page/03_preprocessing (chantier point 15)."""
    return render_template("preprocessing.html", **nav_context("/preprocessing"))


@app.route("/predict", methods=["GET", "POST"])
def predict():
    nav = nav_context("/predict")
    if request.method == "GET":
        return render_template(
            "predict.html", result=None, error=None, filename=None, image_data_uri=None, **nav
        )

    file = request.files.get("file")
    if not file or not file.filename:
        return render_template(
            "predict.html", result=None, error="Aucun fichier sélectionné.", **nav
        )

    file_bytes = file.read()
    image_ctx = {
        "filename": file.filename,
        "image_data_uri": f"data:{file.mimetype};base64,"
        + base64.b64encode(file_bytes).decode("ascii"),
    }

    try:
        r = requests.post(
            f"{BACKEND_URL}/api/v1/predict",
            files={"file": (file.filename, file_bytes, file.mimetype)},
            headers={"X-API-Key": API_KEY},
            timeout=30,
        )
    except requests.exceptions.ConnectionError:
        return render_template(
            "predict.html",
            result=None,
            error=f"Backend inaccessible ({BACKEND_URL}) — lancer : make start",
            **nav,
            **image_ctx,
        )

    if r.status_code != 200:
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        return render_template(
            "predict.html",
            result=None,
            error=f"Erreur {r.status_code} : {detail}",
            **nav,
            **image_ctx,
        )

    return render_template("predict.html", result=r.json(), error=None, **nav, **image_ctx)


@app.route("/architecture")
def architecture():
    """Architecture microservices — frontières HTTP, ports, pipeline DVC/MLflow."""
    return render_template("architecture.html", **nav_context("/architecture"))


@app.route("/monitoring")
def monitoring():
    """Outils de monitoring — MLflow, Prometheus/Grafana, DagsHub, Evidently."""
    return render_template(
        "monitoring.html",
        mlflow_url=MLFLOW_URL,
        grafana_url=GRAFANA_URL,
        prometheus_url=PROMETHEUS_URL,
        dagshub_url=DAGSHUB_URL,
        **nav_context("/monitoring"),
    )


@app.route("/monitoring/drift-report")
def drift_report():
    """Sert le rapport Evidently tel quel (aucun reskin) pour l'iframe de /monitoring."""
    if not DRIFT_REPORT_PATH.exists():
        return (
            "<p style='font-family:monospace;background:#0d1117;color:#ffb3b6;padding:2rem'>"
            "Rapport introuvable localement — lancez <code>dvc pull</code> pour le récupérer."
            "</p>",
            404,
        )
    return send_file(DRIFT_REPORT_PATH)


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

    return render_template(
        "model_status.html", health=health, error=error, **nav_context("/modeles")
    )


if __name__ == "__main__":
    port = int(os.getenv("DEMONSTRATION_PORT", "5051"))
    app.run(host="0.0.0.0", port=port, debug=False)
