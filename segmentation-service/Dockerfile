FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --no-create-home --shell /usr/sbin/nologin appuser

RUN pip install --no-cache-dir --upgrade pip wheel

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

RUN mkdir -p data/models tmp/logs && chown -R appuser:appuser /app

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "segmentation_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
