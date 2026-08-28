FROM python:3.11-slim

WORKDIR /workspace

# curl : requis par HEALTHCHECK. frontend n'utilise ni TensorFlow ni OpenCV (vérifié :
# aucun import tensorflow/cv2/keras dans frontend/**/*.py, cf. CHANTIER_INFRA_SERVICES.md
# point 14) — pas besoin de l'image de base GPU partagée avec trainer.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --create-home --shell /usr/sbin/nologin appuser

COPY requirements.txt /tmp/streamlit.txt

RUN python -m pip install --upgrade pip setuptools wheel \
 && python -m pip install --ignore-installed blinker \
 && python -m pip install -r /tmp/streamlit.txt

COPY . /workspace/frontend/

RUN chown -R appuser:appuser /workspace
ENV HOME=/home/appuser
USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "frontend/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
