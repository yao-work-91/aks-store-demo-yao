"""
Tests for the description generator router.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from main import app
    return TestClient(app)


@pytest.fixture
def mock_completion():
    """Return a mock OpenAI completion response."""
    mock = MagicMock()
    mock.choices[0].message.content = "A wonderful product description."
    return mock


def test_generate_description_openai(client, mock_completion, monkeypatch):
    """Description endpoint uses OpenAI when USE_AZURE_OPENAI is false."""
    monkeypatch.setenv("USE_LOCAL_LLM", "false")
    monkeypatch.setenv("USE_AZURE_OPENAI", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_ORG_ID", "test-org")

    with patch("routers.description_generator._handle_openai", return_value="A wonderful product description.") as mock_openai:
        response = client.post(
            "/generate/description",
            json={"name": "Cat Toy", "tags": ["fun", "interactive"]}
        )

    assert response.status_code == 200
    data = response.json()
    assert "description" in data
    assert data["description"] == "A wonderful product description."
    mock_openai.assert_called_once()


def test_generate_description_azure_openai(client, monkeypatch):
    """Description endpoint uses Azure OpenAI when USE_AZURE_OPENAI is true."""
    monkeypatch.setenv("USE_LOCAL_LLM", "false")
    monkeypatch.setenv("USE_AZURE_OPENAI", "true")
    monkeypatch.setenv("USE_AZURE_AD", "false")

    with patch("routers.description_generator._handle_azure_openai", return_value="Azure description.") as mock_azure:
        response = client.post(
            "/generate/description",
            json={"name": "Dog Treat", "tags": ["healthy", "organic"]}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Azure description."
    mock_azure.assert_called_once()


def test_generate_description_local_llm(client, monkeypatch):
    """Description endpoint uses local LLM when USE_LOCAL_LLM is true."""
    monkeypatch.setenv("USE_LOCAL_LLM", "true")

    with patch("routers.description_generator._handle_local_llm", return_value="Local description.") as mock_local:
        response = client.post(
            "/generate/description",
            json={"name": "Bird Seed", "tags": ["nutritious"]}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Local description."
    mock_local.assert_called_once()


def test_generate_description_error_returns_500(client, monkeypatch):
    """Description endpoint returns HTTP 500 when backend raises an exception."""
    monkeypatch.setenv("USE_LOCAL_LLM", "false")
    monkeypatch.setenv("USE_AZURE_OPENAI", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_ORG_ID", "test-org")

    with patch("routers.description_generator._handle_openai", side_effect=Exception("API error")):
        response = client.post(
            "/generate/description",
            json={"name": "Fish Food", "tags": ["flaky"]}
        )

    assert response.status_code == 500
    assert "Error generating description" in response.json()["detail"]


def test_generate_description_missing_name_returns_422(client):
    """Description endpoint returns 422 when required fields are missing."""
    response = client.post(
        "/generate/description",
        json={"tags": ["fun"]}
    )
    assert response.status_code == 422


def test_generate_description_missing_tags_returns_422(client):
    """Description endpoint returns 422 when tags field is missing."""
    response = client.post(
        "/generate/description",
        json={"name": "Cat Toy"}
    )
    assert response.status_code == 422


def test_handle_openai_missing_credentials(monkeypatch):
    """_handle_openai raises ValueError when OPENAI_API_KEY or OPENAI_ORG_ID is not set."""
    from routers.description_generator import _handle_openai

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_ORG_ID", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY and OPENAI_ORG_ID must be provided"):
        _handle_openai("test prompt")


def test_handle_local_llm_missing_endpoint(monkeypatch):
    """_handle_local_llm raises ValueError when LOCAL_LLM_ENDPOINT is not set."""
    from routers.description_generator import _handle_local_llm

    monkeypatch.delenv("LOCAL_LLM_ENDPOINT", raising=False)

    with pytest.raises(ValueError, match="LOCAL_LLM_ENDPOINT must be provided"):
        _handle_local_llm("test prompt")


def test_handle_azure_openai_missing_deployment(monkeypatch):
    """_handle_azure_openai raises ValueError when deployment or endpoint is not set."""
    from routers.description_generator import _handle_azure_openai

    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT_NAME", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)

    with pytest.raises(ValueError, match="AZURE_OPENAI_DEPLOYMENT_NAME and AZURE_OPENAI_ENDPOINT must be provided"):
        _handle_azure_openai("test prompt", use_azure_ad=False)


def test_handle_azure_openai_missing_api_key(monkeypatch):
    """_handle_azure_openai raises ValueError when API key auth is used but key is missing."""
    from routers.description_generator import _handle_azure_openai

    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-35")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://fake.azure.com/")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY must be provided"):
        _handle_azure_openai("test prompt", use_azure_ad=False)


def test_user_prompt_template_formatting():
    """USER_PROMPT_TEMPLATE formats the product name and tags correctly."""
    from routers.description_generator import USER_PROMPT_TEMPLATE

    prompt = USER_PROMPT_TEMPLATE.format(name="Cat Toy", tags="fun, interactive")

    assert "Cat Toy" in prompt
    assert "fun, interactive" in prompt
