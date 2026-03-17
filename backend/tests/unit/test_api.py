"""Tests API — health, root, config."""

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


# ── Config ────────────────────────────────────────────────────────────────────

def test_settings_defaults():
    assert settings.api_version == "0.1.0"
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 8000
    assert len(settings.class_names) == 4
    assert "COVID" in settings.class_names


def test_settings_img_size():
    assert settings.img_size == (224, 224)


def test_settings_class_names_complete():
    expected = {"COVID", "Lung_Opacity", "Normal", "Viral_Pneumonia"}
    assert set(settings.class_names) == expected


# ── Root ─────────────────────────────────────────────────────────────────────

def test_root_returns_200():
    response = client.get("/")
    assert response.status_code == 200


def test_root_response_keys():
    response = client.get("/")
    data = response.json()
    assert "message" in data
    assert "docs" in data
    assert "health" in data


# ── Health ───────────────────────────────────────────────────────────────────

def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200


def test_health_response_structure():
    response = client.get("/health")
    data = response.json()
    assert "status" in data
    assert "model_loaded" in data
    assert "model_version" in data
    assert "api_version" in data
    assert "classes" in data


def test_health_status_value():
    response = client.get("/health")
    assert response.json()["status"] == "healthy"


def test_health_api_version_matches_settings():
    response = client.get("/health")
    assert response.json()["api_version"] == settings.api_version


def test_health_classes_match_settings():
    response = client.get("/health")
    assert response.json()["classes"] == settings.class_names
