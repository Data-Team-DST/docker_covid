FROM ghcr.io/mon-org/covid-xray-core:latest

WORKDIR /workspace

COPY requirements/trainer.txt /tmp/requirements-trainer.txt
RUN pip install -r /tmp/requirements-trainer.txt

COPY src/ /workspace/src/
COPY app/ /workspace/app/