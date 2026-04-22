#!/bin/sh
set -e

DB_URI="postgresql://${POSTGRES_USER:-mlflow}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-mlflow}"

echo "[mlflow-start] Running db upgrade..."
mlflow db upgrade "$DB_URI" || true

echo "[mlflow-start] Starting server..."
exec mlflow server \
  --host 0.0.0.0 \
  --port 5000 \
  --backend-store-uri "$DB_URI" \
  --default-artifact-root "s3://${MLFLOW_BUCKET:-mlflow}"
