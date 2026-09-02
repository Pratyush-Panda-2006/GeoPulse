import pytest
from unittest.mock import patch, MagicMock
import numpy as np
from src.api.schemas import ChangedRegion
from src.api.services.context_osm import (
    get_osm_context,
    _fetch_overpass_cached,
    _fetch_with_retry,
    PRIMARY_ENDPOINT,
    FALLBACK_ENDPOINTS
)
from src.api.services.evidence_engine import synthesize_evidence
import requests

@pytest.fixture(autouse=True)
def clear_caches():
    _fetch_overpass_cached.cache_clear()

def test_overpass_query_and_geometry_parsing():
    # 1. Overpass query generation syntax and geometry parsing.
    # 2. UTM projection-safe distance computations for nearest roads and water.
    # 3. Building counting within a 500m UTM radius.
    # 4. industrial detection
    
    mock_osm_response = {
        "elements": [
            # A road way
            {
                "type": "way",
                "tags": {"highway": "primary"},
                "geometry": [{"lat": 0.001, "lon": 0.001}, {"lat": 0.002, "lon": 0.002}]
            },
            # A building node right on the centroid
            {
                "type": "node",
                "lat": 0.0,
                "lon": 0.0,
                "tags": {"building": "yes"}
            },
            # A building way outside 500m (roughly 1km away)
            {
                "type": "way",
                "tags": {"building": "yes"},
                "geometry": [{"lat": 0.01, "lon": 0.01}, {"lat": 0.011, "lon": 0.011}]
            },
            # Industrial area
            {
                "type": "way",
                "tags": {"landuse": "industrial"},
                "geometry": [{"lat": 0.0001, "lon": 0.0001}, {"lat": 0.0002, "lon": 0.0002}]
            },
            # Water body
            {
                "type": "way",
                "tags": {"natural": "water"},
                "geometry": [{"lat": -0.001, "lon": -0.001}, {"lat": -0.002, "lon": -0.002}]
            }
        ]
    }
    
    region = ChangedRegion(
        region_id=1, area_px=100, bbox_xy=(0,0,10,10), centroid_xy=(5,5),
        geo_centroid=(0.0, 0.0), geo_bbox=(-0.01, -0.01, 0.01, 0.01),
        mean_change_prob=0.8, severity="High", label="Change"
    )
    
    with patch("src.api.services.context_osm.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_osm_response
        mock_post.return_value = mock_resp
        
        ctx = get_osm_context([region], [-0.01, -0.01, 0.01, 0.01])
        
        assert 1 in ctx
        region_ctx = ctx[1]
        
        assert region_ctx["buildings_within_500m"] == 1
        assert region_ctx["industrial"] is True
        assert region_ctx["nearest_road_m"] is not None
        assert region_ctx["nearest_water_m"] is not None
        assert region_ctx["nearest_road_m"] > 0
        assert region_ctx["nearest_water_m"] > 0
        
        # Test deterministic caching
        get_osm_context([region], [-0.01, -0.01, 0.01, 0.01])
        assert mock_post.call_count == 1

@patch("src.api.services.context_osm.time.sleep")
def test_exponential_backoff_and_fallback(mock_sleep):
    # 4. Exponential backoff and HTTP 429 retry behavior.
    # 5. Fallback endpoint switching upon sustained failures on the primary node.
    
    region = ChangedRegion(
        region_id=1, area_px=100, bbox_xy=(0,0,10,10), centroid_xy=(5,5),
        geo_centroid=(0.0, 0.0), geo_bbox=(-0.01, -0.01, 0.01, 0.01),
        mean_change_prob=0.8, severity="High", label="Change"
    )
    
    with patch("src.api.services.context_osm.requests.post") as mock_post:
        # Mock 429 three times (exhausts primary endpoint)
        # Then 200 on the first fallback endpoint
        
        resp_429 = MagicMock()
        resp_429.status_code = 429
        
        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {"elements": []}
        
        mock_post.side_effect = [resp_429, resp_429, resp_429, resp_200]
        
        ctx = get_osm_context([region], [-0.01, -0.01, 0.01, 0.01])
        
        assert mock_post.call_count == 4
        assert mock_sleep.call_count == 2 # sleeps for attempt 0 and 1, breaks on 2
        
        # Check that fallback was used
        calls = mock_post.call_args_list
        assert calls[0][0][0] == PRIMARY_ENDPOINT
        assert calls[1][0][0] == PRIMARY_ENDPOINT
        assert calls[2][0][0] == PRIMARY_ENDPOINT
        assert calls[3][0][0] == FALLBACK_ENDPOINTS[0]

def test_graceful_degradation():
    # 6. Graceful degradation (returning empty context) on complete timeout/failure.
    
    region = ChangedRegion(
        region_id=1, area_px=100, bbox_xy=(0,0,10,10), centroid_xy=(5,5),
        geo_centroid=(0.0, 0.0), geo_bbox=(-0.01, -0.01, 0.01, 0.01),
        mean_change_prob=0.8, severity="High", label="Change"
    )
    
    with patch("src.api.services.context_osm.requests.post") as mock_post:
        # Exhaust all retries and endpoints
        resp_500 = MagicMock()
        resp_500.status_code = 500
        mock_post.return_value = resp_500
        
        ctx = get_osm_context([region], [-0.01, -0.01, 0.01, 0.01])
        
        assert ctx == {}

def test_evidence_integration():
    # 7. Evidence integration checks ensuring SAR detections aren't removed.
    
    region = ChangedRegion(
        region_id=1, area_px=100, bbox_xy=(0,0,10,10), centroid_xy=(5,5),
        geo_centroid=(0.0, 0.0), geo_bbox=(-0.01, -0.01, 0.01, 0.01),
        mean_change_prob=0.8, severity="High", label="Change"
    )
    
    osm_context = {
        "nearest_road_m": 50.0, # < 100m
        "buildings_within_500m": 0,
        "industrial": True,
        "nearest_water_m": None
    }
    
    mission_config = {"name": "mining"}
    
    evidence = synthesize_evidence(
        region, 
        osm_context=osm_context,
        mission_config=mission_config
    )
    
    assert evidence.evidence_score == 0.45
    assert any("industrial area detected" in c for c in evidence.caveats)
    assert any(s.name == "osm_road_context" for s in evidence.signals)
    assert evidence.context.osm.nearest_road_m == 50.0
