"""Load test — POST /api/v1/predict à 10 req/s (US-15).

Usage :
    make load-test
    # ou directement :
    locust -f scripts/load_test/locustfile.py --headless \
        -u 10 -r 10 --run-time 1m --host http://localhost:8000 \
        --html outputs/load_test/report.html

Le rate limiting (US-12, 100 req/min par défaut) doit être relevé côté
serveur pour ce test — sinon on mesure la vitesse de rejet du limiter,
pas la latence réelle d'inférence. `make load-test` s'en charge via
RATE_LIMIT_PER_MINUTE. La clé API (si `API_KEY` est configurée côté
serveur) est lue depuis la variable d'environnement du même nom.
"""

import os
from pathlib import Path

from locust import HttpUser, constant_throughput, task

SAMPLE_IMAGE = (
    Path(__file__).resolve().parents[2]
    / "data/raw/COVID-19_Radiography_Dataset/COVID/images/COVID-1.png"
)
API_KEY = os.environ.get("API_KEY", "")

if not SAMPLE_IMAGE.exists():
    raise FileNotFoundError(
        f"Image d'exemple introuvable : {SAMPLE_IMAGE}\n"
        "→ dataset non présent localement (dvc pull requis)"
    )

_image_bytes = SAMPLE_IMAGE.read_bytes()


class PredictUser(HttpUser):
    """Un utilisateur simulé = ~1 req/s sur /predict."""

    wait_time = constant_throughput(1)

    @task
    def predict(self):
        headers = {"X-API-Key": API_KEY} if API_KEY else {}
        self.client.post(
            "/api/v1/predict",
            files={"file": ("sample.png", _image_bytes, "image/png")},
            headers=headers,
            name="/api/v1/predict",
        )
