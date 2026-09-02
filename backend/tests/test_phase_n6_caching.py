import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.db import Base
from src.api.schemas import ChangedRegion
from src.api.services.vision_pipeline import orchestrate_vision_classification
from src.api.models.nemotron_cache import NemotronCache

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

@pytest.fixture
def mock_db_session():
    # Setup in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with patch("src.api.db.SessionLocal", TestingSessionLocal):
        yield TestingSessionLocal

@patch("src.api.services.vision_classifier.requests.post")
def test_cache_miss_and_hit(mock_post, monkeypatch, mock_db_session):
    monkeypatch.setenv("NVIDIA_API_KEY", "test_key")
    
    t1, t2 = make_test_arrays()
    r1 = make_region(1)
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"choices": [{"message": {"content": '{"category": "building_structure", "visual_confidence": 0.9, "short_summary": "Test", "visual_cues": ["roof"], "uncertainty": "none"}'}}]}
    mock_post.return_value = mock_response
    
    # 1. Cache miss -> API call
    interpretations = orchestrate_vision_classification(t1, t2, [r1])
    assert interpretations[1].status == "classified"
    assert interpretations[1].category == "building_structure"
    assert mock_post.call_count == 1
    
    # Check DB
    db = mock_db_session()
    caches = db.query(NemotronCache).all()
    assert len(caches) == 1
    db.close()
    
    # 2. Cache hit -> zero API calls
    mock_post.reset_mock()
    interpretations2 = orchestrate_vision_classification(t1, t2, [r1])
    assert interpretations2[1].status == "classified"
    assert interpretations2[1].category == "building_structure"
    assert mock_post.call_count == 0 # no API call made!

@patch("src.api.services.vision_classifier.requests.post")
def test_different_bbox_image_different_keys(mock_post, monkeypatch, mock_db_session):
    monkeypatch.setenv("NVIDIA_API_KEY", "test_key")
    t1, t2 = make_test_arrays()
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"choices": [{"message": {"content": '{"category": "building_structure", "visual_confidence": 0.9, "short_summary": "Test", "visual_cues": ["roof"], "uncertainty": "none"}'}}]}
    mock_post.return_value = mock_response
    
    r1 = make_region(1, bbox=(20, 20, 50, 50))
    r2 = make_region(2, bbox=(21, 21, 51, 51)) # different bbox
    
    orchestrate_vision_classification(t1, t2, [r1])
    assert mock_post.call_count == 1
    
    # different bbox => cache miss => API call
    orchestrate_vision_classification(t1, t2, [r2])
    assert mock_post.call_count == 2
    
    # different image => cache miss
    t2_mod = np.ones((2, 100, 120), dtype=np.float32) * 0.5
    orchestrate_vision_classification(t1, t2_mod, [r1])
    assert mock_post.call_count == 3
    
@patch("src.api.services.vision_classifier.requests.post")
def test_failed_response_not_cached(mock_post, monkeypatch, mock_db_session):
    monkeypatch.setenv("NVIDIA_API_KEY", "test_key")
    t1, t2 = make_test_arrays()
    r1 = make_region(1)
    
    # Malformed response
    mock_response = MagicMock()
    mock_response.json.return_value = {"choices": [{"message": {"content": 'not json'}}]}
    mock_post.return_value = mock_response
    
    orchestrate_vision_classification(t1, t2, [r1])
    assert mock_post.call_count == 1
    
    db = mock_db_session()
    caches = db.query(NemotronCache).all()
    assert len(caches) == 0
    db.close()
    
    # Still calls API again because it wasn't cached
    orchestrate_vision_classification(t1, t2, [r1])
    assert mock_post.call_count == 2
