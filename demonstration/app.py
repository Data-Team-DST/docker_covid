"""Demonstration Flask — DS_COVID MLOps — facade demo produit (contexte, prédicteur, modèles)."""
import base64
import concurrent.futures
import os
from pathlib import Path

import requests
from flask import Flask, render_template, request, send_file

app = Flask(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:5050")
DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://localhost:5001")
SEGMENTATION_SERVICE_URL = os.getenv("SEGMENTATION_SERVICE_URL", "http://localhost:8001")
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
    ("/architecture", "Architecture"),
    ("/modelisation", "Pipeline (DVC & Models)"),
    ("/predict", "Prédicteur"),
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


def _fetch_mask_data_uri(file_bytes: bytes, filename: str, mimetype: str) -> str | None:
    """Masque pulmonaire (U-Net, segmentation-service) pour l'overlay pédagogique de
    /predict — "ce que l'IA regarde". Best-effort : ne bloque jamais la classification
    si le service est indisponible ou lent."""
    try:
        r = requests.post(
            f"{SEGMENTATION_SERVICE_URL}/v1/segment",
            files={"file": (filename, file_bytes, mimetype)},
            timeout=15,
        )
        r.raise_for_status()
    except requests.exceptions.RequestException:
        return None
    return "data:image/png;base64," + base64.b64encode(r.content).decode("ascii")


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

    # Classification (backend) et masque de segmentation (affichage pédagogique) en
    # parallèle — évite de doubler une latence déjà élevée (inférence CPU-only).
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        classify_future = pool.submit(
            requests.post,
            f"{BACKEND_URL}/api/v1/predict",
            files={"file": (file.filename, file_bytes, file.mimetype)},
            headers={"X-API-Key": API_KEY},
            timeout=30,
        )
        mask_future = pool.submit(
            _fetch_mask_data_uri, file_bytes, file.filename, file.mimetype
        )

        try:
            r = classify_future.result()
        except requests.exceptions.ConnectionError:
            return render_template(
                "predict.html",
                result=None,
                error=f"Backend inaccessible ({BACKEND_URL}) — lancer : make start",
                **nav,
                **image_ctx,
            )

        mask_data_uri = mask_future.result()

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

    return render_template(
        "predict.html",
        result=r.json(),
        error=None,
        mask_data_uri=mask_data_uri,
        **nav,
        **image_ctx,
    )


@app.route("/predict/explain", methods=["POST"])
def predict_explain():
    """Grad-CAM à la demande — bouton dédié sur /predict, pas embarqué dans le flux
    principal (cf. TODO.md § Chantier jour J : /explain recalcule classification +
    segmentation en interne, éviter de tripler la charge sur segmentation-service à
    chaque clic par défaut)."""
    file = request.files.get("file")
    if not file or not file.filename:
        return {"error": "Aucun fichier fourni."}, 400

    file_bytes = file.read()
    try:
        r = requests.post(
            f"{BACKEND_URL}/api/v1/explain",
            files={"file": (file.filename, file_bytes, file.mimetype)},
            headers={"X-API-Key": API_KEY},
            timeout=30,
        )
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"error": f"Grad-CAM indisponible ({BACKEND_URL}) — {e}"}, 502

    gradcam_data_uri = "data:image/png;base64," + base64.b64encode(r.content).decode(
        "ascii"
    )
    return {"gradcam_data_uri": gradcam_data_uri}


@app.route("/architecture")
def architecture():
    """Architecture microservices — frontières HTTP, ports, tracking DVC/MLflow/DagsHub."""
    return render_template(
        "architecture.html",
        mlflow_url=MLFLOW_URL,
        dagshub_url=DAGSHUB_URL,
        **nav_context("/architecture"),
    )


@app.route("/monitoring")
def monitoring():
    """Outils de monitoring — Prometheus/Grafana (santé service), Evidently (dérive)."""
    return render_template(
        "monitoring.html",
        grafana_url=GRAFANA_URL,
        prometheus_url=PROMETHEUS_URL,
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


@app.route("/modelisation")
def modelisation():
    """Modélisation : pipeline DVC (dvc.yaml), architecture des deux modèles
    (classification, segmentation) et illustrations qualité — complète /modeles
    (provenance runtime) et /architecture (microservices) sans les dupliquer."""
    try:
        r = requests.get(f"{DATA_SERVICE_URL}/v1/data/stats", timeout=10)
        r.raise_for_status()
        dvc_stats = r.json()
        dvc_error = None
    except requests.exceptions.RequestException as e:
        dvc_stats = None
        dvc_error = f"data-service inaccessible ({DATA_SERVICE_URL}) — {e}"

    return render_template(
        "modelisation.html",
        dvc_stats=dvc_stats,
        dvc_error=dvc_error,
        **nav_context("/modelisation"),
    )


if __name__ == "__main__":
    port = int(os.getenv("DEMONSTRATION_PORT", "5051"))
    app.run(host="0.0.0.0", port=port, debug=False)
