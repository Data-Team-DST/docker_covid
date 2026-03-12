FROM tensorflow/tensorflow:latest-gpu

WORKDIR /workspace

RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    unzip \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt /tmp/requirements-base.txt

RUN python -m pip install --upgrade pip && \
    pip install -r /tmp/requirements-base.txt