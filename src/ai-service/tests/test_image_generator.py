"""
Tests for the image generator router.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from main import app
    return TestClient(app)


def _make_mock_image_response(url="https://example.com/image.png"):
    """Build a mock Azure OpenAI image response."""
    mock_image_data = MagicMock()
    mock_image_data.url = url

    mock_response = MagicMock()
    mock_response.model_dump_json.return_value = (
        f'{{"data": [{{"url": "{url}"}}]}}'
    )
    return mock_response


def test_generate_image_success(client, monkeypatch):
    """Image endpoint returns an image URL on success."""
    monkeypatch.setenv("AZURE_OPENAI_DALLE_ENDPOINT", "https://fake.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_DALLE_DEPLOYMENT_NAME", "dall-e-3")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("USE_AZURE_AD", "false")

    expected_url = "https://example.com/generated.png"

    with patch("routers.image_generator._handle_azure_openai", return_value=expected_url) as mock_handler:
        response = client.post(
            "/generate/image",
            json={"name": "Cat Toy", "description": "A fun toy for cats"}
        )

    assert response.status_code == 200
    data = response.json()
    assert "image" in data
    assert data["image"] == expected_url
    mock_handler.assert_called_once()


def test_generate_image_error_returns_500(client, monkeypatch):
    """Image endpoint returns HTTP 500 when backend raises an exception."""
    monkeypatch.setenv("USE_AZURE_AD", "false")

    with patch("routers.image_generator._handle_azure_openai", side_effect=Exception("API error")):
        response = client.post(
            "/generate/image",
            json={"name": "Fish Food", "description": "Nutritious fish food"}
        )

    assert response.status_code == 500
    assert "Error generating image" in response.json()["detail"]


def test_generate_image_missing_name_returns_422(client):
    """Image endpoint returns 422 when name field is missing."""
    response = client.post(
        "/generate/image",
        json={"description": "A fun toy"}
    )
    assert response.status_code == 422


def test_generate_image_missing_description_returns_422(client):
    """Image endpoint returns 422 when description field is missing."""
    response = client.post(
        "/generate/image",
        json={"name": "Cat Toy"}
    )
    assert response.status_code == 422


def test_handle_azure_openai_missing_endpoint(monkeypatch):
    """_handle_azure_openai raises ValueError when neither DALL-E endpoint is configured."""
    from routers.image_generator import _handle_azure_openai

    monkeypatch.delenv("AZURE_OPENAI_DALLE_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)

    with pytest.raises(ValueError, match="AZURE_OPENAI_DALLE_ENDPOINT or AZURE_OPENAI_ENDPOINT must be provided"):
        _handle_azure_openai("test prompt", use_azure_ad=False)


def test_handle_azure_openai_missing_deployment(monkeypatch):
    """_handle_azure_openai raises ValueError when deployment name is not set."""
    from routers.image_generator import _handle_azure_openai

    monkeypatch.setenv("AZURE_OPENAI_DALLE_ENDPOINT", "https://fake.azure.com/")
    monkeypatch.delenv("AZURE_OPENAI_DALLE_DEPLOYMENT_NAME", raising=False)

    with pytest.raises(ValueError, match="AZURE_OPENAI_DALLE_DEPLOYMENT_NAME must be provided"):
        _handle_azure_openai("test prompt", use_azure_ad=False)


def test_handle_azure_openai_missing_api_version(monkeypatch):
    """_handle_azure_openai raises ValueError when API version is not set."""
    from routers.image_generator import _handle_azure_openai

    monkeypatch.setenv("AZURE_OPENAI_DALLE_ENDPOINT", "https://fake.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_DALLE_DEPLOYMENT_NAME", "dall-e-3")
    monkeypatch.delenv("AZURE_OPENAI_API_VERSION", raising=False)

    with pytest.raises(ValueError, match="AZURE_OPENAI_API_VERSION must be provided"):
        _handle_azure_openai("test prompt", use_azure_ad=False)


def test_handle_azure_openai_missing_api_key(monkeypatch):
    """_handle_azure_openai raises ValueError when API key auth is used but key is missing."""
    from routers.image_generator import _handle_azure_openai

    monkeypatch.setenv("AZURE_OPENAI_DALLE_ENDPOINT", "https://fake.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_DALLE_DEPLOYMENT_NAME", "dall-e-3")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY must be provided"):
        _handle_azure_openai("test prompt", use_azure_ad=False)


def test_user_prompt_template_formatting():
    """USER_PROMPT_TEMPLATE formats the product name and description correctly."""
    from routers.image_generator import USER_PROMPT_TEMPLATE

    prompt = USER_PROMPT_TEMPLATE.format(name="Cat Toy", description="A fun toy for cats")

    assert "Cat Toy" in prompt
    assert "A fun toy for cats" in prompt
