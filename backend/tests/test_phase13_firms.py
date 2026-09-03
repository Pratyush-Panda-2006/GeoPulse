import pytest
from unittest.mock import patch, MagicMock
from src.api.services.context_fire import get_fire_context, _fetch_firms_chunk, _haversine_distance
from src.api.services.evidence_engine import synthesize_evidence
from src.api.schemas import ChangedRegion

def test_haversine_distance():
    # 6. nearest-distance calculation
    # Dist from (0,0) to (0, 0.01) is about 1.11 km
    dist = _haversine_distance(0.0, 0.0, 0.0, 0.01)
    assert 1.10 < dist < 1.12

def test_missing_key_handling():
    # 8. missing-key handling
    with patch.dict('os.environ', {}, clear=True):
        ctx = get_fire_context([], [0,0,1,1], "2024-01-01", "2024-01-05")
        assert ctx == {}

def test_firms_chunking_and_source_selection():
    # 1. <=10-day chunking
    # 2. multi-month period
    # 3. source selection by data age
    # 7. deterministic caching
    
    _fetch_firms_chunk.cache_clear()
    
    with patch('os.environ.get', return_value="fake_key"), \
         patch('src.api.services.context_fire._fetch_firms_chunk', return_value=[]) as mock_fetch, \
         patch('src.api.services.context_fire.datetime') as mock_dt:
        
        from datetime import datetime, timedelta
        # Mock "now" to be 2024-04-01
        mock_dt.now.return_value = datetime(2024, 4, 1)
        mock_dt.strptime = datetime.strptime
        
        # Request from Jan 1 to Feb 15 (46 days)
        # 5 chunks of 10 days
        get_fire_context([], [0,0,1,1], "2024-01-01", "2024-02-15")
        
        assert mock_fetch.call_count == 5
        # Check source for first call
        args, _ = mock_fetch.call_args_list[0]
        assert args[1] == "VIIRS_SNPP_SP"
        assert args[3] == 10 # 10 days duration
        
        # Test recent request (within 14 days)
        mock_fetch.reset_mock()
        get_fire_context([], [0,0,1,1], "2024-03-25", "2024-03-31")
        assert mock_fetch.call_count == 1
        args, _ = mock_fetch.call_args_list[0]
        assert args[1] == "VIIRS_SNPP_NRT"
        assert args[3] == 7 # 7 days duration

def test_firms_parsing_and_hotspot_filtering():
    # 4. FIRMS response parsing
    # 5. hotspot filtering
    # 9. HTTP/rate-limit failure
    
    mock_csv = b"latitude,longitude,acq_date\n0.005,0.005,2024-01-01\n10.0,10.0,2024-01-02"
    
    region = ChangedRegion(
        region_id=1, area_px=4, centroid_xy=(0,0), bbox_xy=(0,0,1,1),
        geo_centroid=(0.0, 0.0), mean_change_prob=0.8, severity="Medium", label="Change"
    )
    
    class MockResponse:
        def read(self): return mock_csv
        def __enter__(self): return self
        def __exit__(self, *args): pass
        
    _fetch_firms_chunk.cache_clear()
    with patch('os.environ.get', return_value="fake_key"), \
         patch('urllib.request.urlopen', return_value=MockResponse()):
        ctx = get_fire_context([region], [0,0,1,1], "2024-01-01", "2024-01-01")
        
        assert 1 in ctx
        fire_ctx = ctx[1]
        
        assert fire_ctx["nearby"] is True
        assert fire_ctx["count"] == 1 # Only one is nearby (dist < 2km)
        assert fire_ctx["nearest_km"] < 2.0
        assert "2024-01-01" in fire_ctx["dates"]
        
    # Test graceful failure on HTTP error
    _fetch_firms_chunk.cache_clear()
    import urllib.error
    with patch('os.environ.get', return_value="fake_key"), \
         patch('urllib.request.urlopen', side_effect=urllib.error.URLError("Rate limited")):
        ctx = get_fire_context([region], [0,0,1,1], "2024-01-01", "2024-01-01")
        
        assert 1 in ctx
        fire_ctx = ctx[1]
        assert fire_ctx["nearby"] is False
        assert fire_ctx["count"] == 0
        assert fire_ctx["nearest_km"] is None

def test_evidence_integration_preserves_sar():
    # 11. EvidenceObject receives fire context without changing Model 3 detections
    region = ChangedRegion(
        region_id=1, area_px=4, centroid_xy=(0,0), bbox_xy=(0,0,1,1),
        geo_centroid=(0.0, 0.0), mean_change_prob=0.85, severity="Medium", label="Change"
    )
    
    fire_ctx = {
        "nearby": True,
        "count": 5,
        "nearest_km": 0.5,
        "dates": ["2024-01-01"]
    }
    
    # Before
    ev_before = synthesize_evidence(region, fire_context=None)
    sar_sig_before = next(s for s in ev_before.signals if s.name == "sar_backscatter_anomaly")
    
    # After
    ev_after = synthesize_evidence(region, fire_context=fire_ctx)
    sar_sig_after = next(s for s in ev_after.signals if s.name == "sar_backscatter_anomaly")
    fire_sig_after = next((s for s in ev_after.signals if s.name == "active_fire_detected"), None)
    
    # Assert SAR probability is untouched
    assert sar_sig_before.value == sar_sig_after.value == 0.85
    assert fire_sig_after is not None
    assert fire_sig_after.value == 5
    assert ev_after.context.fire.model_dump() == fire_ctx
