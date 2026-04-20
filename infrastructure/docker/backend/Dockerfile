FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip wheel

WORKDIR /app

# Requirements séparés pour profiter du cache Docker
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code source
COPY backend/app ./app

# Données/modèles montés en volume, pas copiés dans l'image
RUN mkdir -p data/models data/raw data/processed

EXPOSE 8000

# Healthcheck intégré
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
