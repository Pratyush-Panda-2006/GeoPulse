import os
import pytest
import requests
from unittest.mock import patch, MagicMock
from src.api.services.vision_classifier import VisionClassifierClient

def test_endpoint_and_model_configured():
    client = VisionClassifierClient(api_key="dummy")
    assert client.endpoint == "https://integrate.api.nvidia.com/v1/chat/completions"
    assert client.model == "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"

def test_missing_api_key_handling():
    with patch.dict(os.environ, {}, clear=True):
        client = VisionClassifierClient(api_key=None)
        with pytest.raises(ValueError, match="Missing NVIDIA_API_KEY"):
            client.classify_image("sys", "user")

@patch("src.api.services.vision_classifier.requests.post")
def test_correct_request_configuration(mock_post):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"choices": [{"message": {"content": "parsed_content_result"}}]}
    mock_post.return_value = mock_resp
    
    client = VisionClassifierClient(api_key="secret-key")
    result = client.classify_image("sys", "user")
    
    assert result == "parsed_content_result"
    mock_post.assert_called_once()
    
    # 3. NVIDIA_API_KEY usage
    kwargs = mock_post.call_args.kwargs
    assert kwargs["headers"]["Authorization"] == "Bearer secret-key"
    
    # 4, 5, 6. temperature=0, max_tokens cap, no tools field
    payload = kwargs["json"]
    assert payload["temperature"] == 0.0
    assert payload["max_tokens"] == 300
    assert "tools" not in payload
    
    # 7. response read from content is verified by the assert result == "parsed_content_result"

@patch("src.api.services.vision_classifier.requests.post")
def test_timeout_and_retry_behavior(mock_post):
    # Mocking a timeout exception for first 2 calls, then success on 3rd
    mock_post.side_effect = [
        requests.exceptions.Timeout("Timeout 1"),
        requests.exceptions.Timeout("Timeout 2"),
        MagicMock(json=lambda: {"choices": [{"message": {"content": "success"}}]})
    ]
    
    client = VisionClassifierClient(api_key="secret-key")
    with patch("src.api.services.vision_classifier.time.sleep") as mock_sleep:
        result = client.classify_image("sys", "user")
        
        assert result == "success"
        assert mock_post.call_count == 3
        # Ensure it sleeps for backoff
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)

@patch("src.api.services.vision_classifier.requests.post")
def test_timeout_exhaustion(mock_post):
    mock_post.side_effect = requests.exceptions.Timeout("Timeout")
    
    client = VisionClassifierClient(api_key="secret-key")
    with patch("src.api.services.vision_classifier.time.sleep"):
        with pytest.raises(TimeoutError, match="timed out after 3 retries"):
            client.classify_image("sys", "user")
            
    assert mock_post.call_count == 3
