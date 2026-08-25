FROM python:3.11-slim
WORKDIR /app

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --no-create-home --shell /usr/sbin/nologin appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

RUN mkdir -p /app/tmp/logs && chown -R appuser:appuser /app

USER appuser

EXPOSE 5002
CMD ["python", "app.py"]
