"""
Tests for the main FastAPI application module.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from main import app
    return TestClient(app)


def test_health_no_dalle(client, monkeypatch):
    """Health endpoint returns ok and only description capability when DALL-E is not configured."""
    monkeypatch.delenv("AZURE_OPENAI_DALLE_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_DALLE_DEPLOYMENT_NAME", raising=False)

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "description" in data["capabilities"]
    assert "image" not in data["capabilities"]


def test_health_with_dalle_endpoint(client, monkeypatch):
    """Health endpoint includes image capability when DALL-E endpoint and deployment are set."""
    monkeypatch.setenv("AZURE_OPENAI_DALLE_ENDPOINT", "https://fake.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_DALLE_DEPLOYMENT_NAME", "dall-e-3")

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "description" in data["capabilities"]
    assert "image" in data["capabilities"]


def test_health_with_openai_endpoint_and_dalle_deployment(client, monkeypatch):
    """Health endpoint includes image capability when AZURE_OPENAI_ENDPOINT and deployment are set."""
    monkeypatch.delenv("AZURE_OPENAI_DALLE_ENDPOINT", raising=False)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://fake.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_DALLE_DEPLOYMENT_NAME", "dall-e-3")

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "image" in data["capabilities"]


def test_health_dalle_deployment_missing(client, monkeypatch):
    """Health endpoint excludes image capability when DALL-E deployment name is not set."""
    monkeypatch.setenv("AZURE_OPENAI_DALLE_ENDPOINT", "https://fake.openai.azure.com/")
    monkeypatch.delenv("AZURE_OPENAI_DALLE_DEPLOYMENT_NAME", raising=False)

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "image" not in data["capabilities"]


def test_health_returns_version(client, monkeypatch):
    """Health endpoint returns the version in its response."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "version" in data
