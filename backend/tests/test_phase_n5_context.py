import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from src.api.schemas import ChangedRegion
from src.api.services.vision_pipeline import orchestrate_vision_classification

def make_test_arrays():
    t1 = np.zeros((2, 100, 120), dtype=np.float32)
    t2 = np.ones((2, 100, 120), dtype=np.float32)
    return t1, t2

def make_region(region_id, severity="High", bbox=(20, 20, 50, 50), evidence_dict=None):
    region = ChangedRegion(
        region_id=region_id,
        area_px=100,
        centroid_xy=(35.0, 35.0),
        bbox_xy=bbox,
        severity=severity
    )
    if evidence_dict is not None:
        mock_evidence = MagicMock()
        mock_evidence.dict.return_value = evidence_dict
        region.evidence = mock_evidence
    return region

@patch("src.api.services.vision_classifier.requests.post")
def test_context_absent_preserves_prompt(mock_post, monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test_key")
    
    t1, t2 = make_test_arrays()
    r1 = make_region(1)
    
    assert r1.evidence is None
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"choices": [{"message": {"content": '{"category": "building_structure", "visual_confidence": 0.9}'}}]}
    mock_post.return_value = mock_response
    
    orchestrate_vision_classification(t1, t2, [r1])
    
    payload = mock_post.call_args[1]["json"]
    user_text = payload["messages"][1]["content"][0]["text"]
    
    assert "CONTEXTUAL EVIDENCE" not in user_text

@patch("src.api.services.vision_classifier.requests.post")
def test_context_present_injects_prompt(mock_post, monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test_key")
    
    t1, t2 = make_test_arrays()
    r1 = make_region(1, evidence_dict={"water": "flooded", "fire": "none"})
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"choices": [{"message": {"content": '{"category": "flood_water_expansion", "visual_confidence": 0.8}'}}]}
    mock_post.return_value = mock_response
    
    orchestrate_vision_classification(t1, t2, [r1])
    
    payload = mock_post.call_args[1]["json"]
    user_text = payload["messages"][1]["content"][0]["text"]
    
    assert "--- CONTEXTUAL EVIDENCE ---" in user_text
    assert "'water': 'flooded'" in user_text
    assert "Never override Model 3 detection or probability" in user_text
    assert "visual evidence remains primary" in user_text

@patch("src.api.services.vision_classifier.requests.post")
def test_context_empty_dict_does_not_inject(mock_post, monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test_key")
    
    t1, t2 = make_test_arrays()
    r1 = make_region(1, evidence_dict={})
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"choices": [{"message": {"content": '{"category": "building_structure", "visual_confidence": 0.9}'}}]}
    mock_post.return_value = mock_response
    
    orchestrate_vision_classification(t1, t2, [r1])
    
    payload = mock_post.call_args[1]["json"]
    user_text = payload["messages"][1]["content"][0]["text"]
    
    assert "CONTEXTUAL EVIDENCE" not in user_text
