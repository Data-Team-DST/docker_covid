FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir \
       mlflow==2.19.0 \
       boto3==1.34.0 \
       psycopg2-binary==2.9.9

COPY infrastructure/docker/mlflow/start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 5000
ENTRYPOINT ["/start.sh"]
