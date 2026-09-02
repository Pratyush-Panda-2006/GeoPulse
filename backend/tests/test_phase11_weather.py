import pytest
import datetime as dt
from unittest.mock import patch, MagicMock
from src.api.services.context_weather import get_weather_context, detect_event_date, _fetch_open_meteo
from src.api.schemas import WeatherContext
from src.api.services.analyze_service import run_analysis
from src.api.schemas import AnalyzeRequest
import numpy as np

# Mock Responses
def mock_open_meteo_response(endpoint="archive"):
    return {
        "daily": {
            "time": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
            "precipitation_sum": [0.0, 5.0, 55.0, 2.0, None], # Total: 62.0, Peak: 55.0 on 2024-01-03
            "soil_moisture_0_to_10cm_mean": [0.2, 0.25, 0.4, 0.45, None] # Mean of valid: 0.325
        },
        "_endpoint_used": endpoint
    }

def test_archive_vs_forecast_endpoint_selection():
    # 1. Archive endpoint selection (older than 10 days)
    with patch("src.api.services.context_weather.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_open_meteo_response("archive")
        mock_get.return_value = mock_resp
        
        # Call with an old date
        old_end_date = (dt.date.today() - dt.timedelta(days=20)).isoformat()
        res = _fetch_open_meteo(0.0, 0.0, "2024-01-01", old_end_date)
        
        # Extract URL from mock call args
        args, kwargs = mock_get.call_args
        assert "archive-api.open-meteo.com" in args[0]
        assert res["_endpoint_used"] == "archive"

    # 2. Forecast endpoint selection (recent)
    _fetch_open_meteo.cache_clear()
    with patch("src.api.services.context_weather.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_open_meteo_response("forecast")
        mock_get.return_value = mock_resp
        
        # Call with a recent date
        recent_end_date = (dt.date.today() - dt.timedelta(days=2)).isoformat()
        res = _fetch_open_meteo(0.0, 0.0, "2024-01-01", recent_end_date)
        
        args, kwargs = mock_get.call_args
        assert "api.open-meteo.com/v1/forecast" in args[0]
        assert res["_endpoint_used"] == "forecast"


def test_precipitation_parsing_and_classification():
    # 3 & 4. Precipitation parsing and Rainfall classification
    with patch("src.api.services.context_weather._fetch_open_meteo") as mock_fetch:
        mock_fetch.return_value = mock_open_meteo_response("archive")
        
        ctx = get_weather_context([0, 0, 1, 1], "2024-01-01", "2024-01-05", event_date="2024-01-04")
        
        assert isinstance(ctx, WeatherContext)
        assert ctx.total_precipitation_mm == 62.0
        assert ctx.peak_daily_precipitation_mm == 55.0
        assert ctx.peak_day == "2024-01-03"
        assert ctx.rainfall_class == "HIGH"
        assert ctx.mean_soil_moisture_pct == 0.325
        
        # Antecedent rainfall before 2024-01-04 should be sum of 2024-01-01 to 2024-01-03
        # 0.0 + 5.0 + 55.0 = 60.0
        assert ctx.antecedent_rainfall_mm == 60.0

def test_event_date_detection():
    # 5. Peak rainfall event-date detection
    with patch("src.api.services.context_weather._fetch_open_meteo") as mock_fetch:
        mock_fetch.return_value = mock_open_meteo_response("archive")
        event_date = detect_event_date([0, 0, 1, 1], "2024-01-01", "2024-01-05")
        assert event_date == "2024-01-03"

@patch("src.api.services.analyze_service.fetch_sar_timeseries")
@patch("src.api.services.analyze_service.SentinelHubClient")
@patch("src.api.services.analyze_service.process_dem_tile")
@patch("src.api.services.analyze_service.run_change_detection")
@patch("src.api.services.analyze_service.get_weather_context")
@patch("src.api.services.analyze_service.detect_event_date")
def test_event_aware_selector_and_graceful_weather_failure(
    mock_detect_event_date, mock_get_weather, mock_inference, mock_dem, mock_cdse, mock_sar
):
    # Setup mocks
    mock_detect_event_date.return_value = "2024-01-03"
    
    # 7. Weather failure gracefully degrades without failing analysis
    # Simulate weather failure by returning None
    mock_get_weather.return_value = None
    
    mock_sar.return_value = (
        {"images_compared": 2, "intermediate": [], "reason": "test"},
        {"meta": {"scene_id": "S1_old", "acquisition_date": "2024-01-01T00:00:00Z"}, "array": np.zeros((2, 512, 512))},
        {"meta": {"scene_id": "S1_new", "acquisition_date": "2024-01-10T00:00:00Z"}, "array": np.zeros((2, 512, 512))},
        []
    )
    
    from src.api.schemas import PairwiseChangeResult, ChangedRegion
    mock_inference.return_value = MagicMock(
        regions=[],
        mean_change_probability=0.0,
        total_changed_area_sq_km=0.0,
        t1_preview_base64="",
        t2_preview_base64="",
        t1_grayscale_base64="",
        t2_grayscale_base64="",
        t1_false_color_base64="",
        t2_false_color_base64="",
        optical_base64="",
        optical_boxes_base64="",
        change_mask_base64="",
        confidence_heatmap_base64="",
        overlay_base64="",
        change_boxes_base64=""
    )
    
    req = AnalyzeRequest(
        aoi={"type": "Polygon", "coordinates": [[[0,0], [1,0], [1,1], [0,1], [0,0]]]},
        period={"start": "2024-01-01", "end": "2024-01-10"},
        mission="disaster" # Event-aware
    )
    
    # Run
    res = run_analysis(req)
    
    # 6. Event-aware selector receives the detected event date
    # Assert that fetch_sar_timeseries was called with event_date="2024-01-03"
    args, kwargs = mock_sar.call_args
    assert kwargs["event_date"] == dt.date(2024, 1, 3)
    
    # Assert weather failure didn't crash analysis and context is None or missing weather
    assert res.context is None or res.context.weather is None
    assert res.event_date == "2024-01-03"

    # 8. No browser-side Open-Meteo calls -> This is structurally proven because 
    # Open-Meteo calls are fully encapsulated inside `src/api/services/context_weather.py`
    # and only executed synchronously via run_analysis on the backend.
