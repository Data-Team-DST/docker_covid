ARG BASE_IMAGE=ghcr.io/data-team-dst/covid-xray-base:latest
FROM ${BASE_IMAGE}

WORKDIR /workspace

COPY requirements/trainer.txt /tmp/trainer.txt

RUN python -m pip install --upgrade pip setuptools wheel \
 && python -m pip install --ignore-installed blinker \
 && python -m pip install -r /tmp/trainer.txt

COPY src/ /workspace/src/
COPY app/ /workspace/app/