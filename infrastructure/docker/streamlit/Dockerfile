ARG BASE_IMAGE=ghcr.io/data-team-dst/covid-xray-base:latest
FROM ${BASE_IMAGE}

WORKDIR /workspace

COPY requirements/streamlit.txt /tmp/streamlit.txt

RUN python -m pip install --upgrade pip setuptools wheel \
 && python -m pip install --ignore-installed blinker \
 && python -m pip install -r /tmp/streamlit.txt

COPY backend/src/ /workspace/src/
COPY frontend/ /workspace/frontend/

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "frontend/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]