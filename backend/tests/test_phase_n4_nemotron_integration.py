import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from src.api.schemas import ChangedRegion
from src.api.services.vision_pipeline import orchestrate_vision_classification
from src.api.services.vision_classifier import VisionClassifierClient, NEMOTRON_SYSTEM_PROMPT

def make_test_arrays():
    t1 = np.zeros((2, 100, 120), dtype=np.float32)
    t2 = np.ones((2, 100, 120), dtype=np.float32)
    return t1, t2

def make_region(region_id, severity="High", bbox=(20, 20, 50, 50)):
    return ChangedRegion(
        region_id=region_id,
        area_px=100,
        centroid_xy=(35.0, 35.0),
        bbox_xy=bbox,
        severity=severity
    )

def mock_successful_response():
    return {
        "choices": [
            {
                "message": {
                    "content": '{"category": "building_structure", "visual_confidence": 0.8, "short_summary": "Test", "visual_cues": ["c1"], "uncertainty": "none"}'
                }
            }
        ]
    }

@patch("src.api.services.vision_classifier.requests.post")
def test_multimodal_request_payload(mock_post, monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test_key")
    
    mock_response = MagicMock()
    mock_response.json.return_value = mock_successful_response()
    mock_post.return_value = mock_response

    t1, t2 = make_test_arrays()
    region = make_region(1, severity="High")
    
    interpretations = orchestrate_vision_classification(t1, t2, [region])
    
    assert 1 in interpretations
    assert interpretations[1].status == "classified"
    
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    payload = kwargs["json"]
    
    messages = payload["messages"]
    assert len(messages) == 2
    
    # 3. system prompt preserved
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == NEMOTRON_SYSTEM_PROMPT
    
    # 1. multimodal request payload contains image_url
    assert messages[1]["role"] == "user"
    user_content = messages[1]["content"]
    assert isinstance(user_content, list)
    assert len(user_content) == 2
    
    # 4. user text preserved
    assert user_content[0]["type"] == "text"
    assert "Model 3 has already detected" in user_content[0]["text"]
    
    # 2. JPEG becomes a valid base64 data URI
    assert user_content[1]["type"] == "image_url"
    data_uri = user_content[1]["image_url"]["url"]
    assert data_uri.startswith("data:image/jpeg;base64,")

@patch("src.api.services.vision_classifier.requests.post")
def test_gating_logic(mock_post, monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test_key")
    
    t1, t2 = make_test_arrays()
    r1 = make_region(1, severity="High")
    r2 = make_region(2, severity="Medium") # 6. non-HIGH skipped
    r3 = make_region(3, severity="High", bbox=(10, 10, 15, 15)) # 7. too-small skipped
    
    import requests
    mock_post.side_effect = requests.exceptions.Timeout("Mock timeout")
    
    interpretations = orchestrate_vision_classification(t1, t2, [r1, r2, r3])
    
    assert interpretations[1].status == "unavailable" # reaches classifier
    assert interpretations[2].status == "skipped_non_high"
    assert interpretations[3].status == "skipped_small_crop"
    
    # 5. HIGH region reaches classifier (with 1 retry due to override)
    assert mock_post.call_count == 1

@patch("src.api.services.vision_classifier.requests.post")
def test_three_call_ceiling(mock_post, monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test_key")
    
    mock_response = MagicMock()
    mock_response.json.return_value = mock_successful_response()
    mock_post.return_value = mock_response

    t1, t2 = make_test_arrays()
    # 5 eligible HIGH regions
    regions = [make_region(i) for i in range(1, 6)]
    
    interpretations = orchestrate_vision_classification(t1, t2, regions)
    
    # 8. first 3 eligible HIGH regions are callable
    assert interpretations[1].status == "classified"
    assert interpretations[2].status == "classified"
    assert interpretations[3].status == "classified"
    
    # 9. 4th+ eligible region gets call_limit_reached
    assert interpretations[4].status == "call_limit_reached"
    assert interpretations[5].status == "call_limit_reached"
    
    assert mock_post.call_count == 3

@patch("src.api.services.vision_classifier.requests.post")
def test_responses_and_failures(mock_post, monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test_key")
    
    t1, t2 = make_test_arrays()
    r1 = make_region(1)
    
    # 10. successful response is parsed through N2 parser
    # 14. category is preserved correctly
    mock_response = MagicMock()
    mock_response.json.return_value = mock_successful_response()
    mock_post.return_value = mock_response
    interpretations = orchestrate_vision_classification(t1, t2, [r1])
    assert interpretations[1].status == "classified"
    assert interpretations[1].category == "building_structure"
    assert interpretations[1].visual_confidence == 0.8
    
    # 11. malformed response becomes malformed_response
    # 16. no fake category is produced on failure
    mock_post.reset_mock()
    mock_response.json.return_value = {"choices": [{"message": {"content": "not json"}}]}
    mock_post.return_value = mock_response
    interpretations = orchestrate_vision_classification(t1, t2, [r1])
    assert interpretations[1].status == "malformed_response"
    assert interpretations[1].category is None
    assert interpretations[1].error is not None
    
    # 12. timeout/API failure becomes unavailable
    import requests
    mock_post.reset_mock()
    mock_post.side_effect = requests.exceptions.Timeout("Timed out")
    interpretations = orchestrate_vision_classification(t1, t2, [r1])
    assert interpretations[1].status == "unavailable"
    assert interpretations[1].category is None
    assert "timed out" in interpretations[1].error.lower()
