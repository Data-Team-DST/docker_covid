ARG BASE_IMAGE
FROM ${BASE_IMAGE}

WORKDIR /workspace

COPY requirements/trainer.txt /tmp/trainer.txt
RUN pip install -r /tmp/trainer.txt

COPY src/ /workspace/src/
COPY app/ /workspace/app/