FROM tensorflow/tensorflow:2.21.0-gpu

WORKDIR /workspace

RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    unzip \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --create-home --shell /usr/sbin/nologin appuser
# Utilisateur créé ici mais pas activé (pas de USER) : cette image de base sert
# aussi à trainer/, qui doit rester root (accès GPU/device). streamlit/
# l'active explicitement dans son propre Dockerfile.

COPY infrastructure/docker/base/requirements.txt /tmp/requirements-base.txt

RUN python -m pip install --upgrade pip && \
    pip install -r /tmp/requirements-base.txt