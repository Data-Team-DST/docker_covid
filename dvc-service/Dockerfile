FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install --no-install-recommends -y git && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --create-home --shell /usr/sbin/nologin appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown -R appuser:appuser /app

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV HOME=/home/appuser

USER appuser

EXPOSE 5003

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5003/health')"

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "dvc_service.main:app", "--host", "0.0.0.0", "--port", "5003"]
