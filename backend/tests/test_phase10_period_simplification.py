import pytest
from unittest.mock import patch, MagicMock
from src.api.routers.detect import detect_timeseries_changes
from src.api.schemas import TimeSeriesRequest
from src.data_ingestion.sar_timeseries import fetch_sar_timeseries
import numpy as np
import asyncio

@patch("src.api.routers.detect.db.init_db")
@patch("src.api.routers.detect.fetch_sar_timeseries")
@patch("src.api.services.inference_service.run_change_detection")
@patch("src.api.routers.detect.db.SessionLocal")
def test_period_simplification_calls(mock_session, mock_inference, mock_fetch, mock_init_db):
    # Mock N scenes -> 2 downloads output format
    mock_all_meta = [
        {"scene_id": "scene_1", "acquisition_date": "2024-01-01", "orbit_state": "ascending", "relative_orbit": 59, "mode": "IW", "polarizations": ["VV", "VH"]},
        {"scene_id": "scene_2", "acquisition_date": "2024-02-01", "orbit_state": "ascending", "relative_orbit": 59, "mode": "IW", "polarizations": ["VV", "VH"]},
        {"scene_id": "scene_3", "acquisition_date": "2024-03-01", "orbit_state": "ascending", "relative_orbit": 59, "mode": "IW", "polarizations": ["VV", "VH"]}
    ]
    
    mock_t1_dict = {
        "meta": mock_all_meta[0],
        "array": np.zeros((2, 512, 512), dtype=np.float32)
    }
    
    mock_t2_dict = {
        "meta": mock_all_meta[2],
        "array": np.zeros((2, 512, 512), dtype=np.float32)
    }
    
    mock_selection = {
        "t1": mock_all_meta[0],
        "t2": mock_all_meta[2],
        "intermediate": [mock_all_meta[1]],
        "images_compared": 2,
        "strategy": "progressive",
        "reason": "mock"
    }
    
    mock_fetch.return_value = (mock_selection, mock_t1_dict, mock_t2_dict, mock_all_meta)
    
    # Mock single inference result
    mock_inference_result = MagicMock()
    mock_inference_result.regions = []
    mock_inference_result.change_percentage = 0.5
    mock_inference_result.num_change_clusters = 1
    mock_inference_result.total_changed_area_sq_km = 0.1
    mock_inference_result.t1_preview_base64 = "base64"
    mock_inference_result.t2_preview_base64 = "base64"
    mock_inference_result.change_mask_base64 = "base64"
    mock_inference_result.confidence_heatmap_base64 = "base64"
    mock_inference_result.overlay_base64 = "base64"
    
    mock_inference.return_value = mock_inference_result
    
    # Create mock session
    mock_session_instance = MagicMock()
    mock_session.return_value = mock_session_instance
    
    # Mock _get_or_create_scene inside detect.py
    with patch("src.api.routers.detect._get_or_create_scene") as mock_get_scene:
        mock_scene = MagicMock()
        mock_scene.id = 1
        mock_get_scene.return_value = mock_scene
        
        # Run the endpoint directly
        req = TimeSeriesRequest(
            bbox={"min_lon": -1, "min_lat": -1, "max_lon": 1, "max_lat": 1},
            date_range=["2024-01-01", "2024-03-01"],
            model_name="snunet_cd_sar"
        )
        
        res = asyncio.run(detect_timeseries_changes(req))
        
        # Assertions proving N scenes -> 2 used -> 1 inference
        assert mock_fetch.call_count == 1
        assert mock_inference.call_count == 1
        
        assert res.acquisitions_found == 3
        assert res.acquisitions_used == 2
        assert len(res.all_acquisitions) == 3
        
        # Test new metadata fields
        assert res.all_acquisitions[0].orbit_state == "ascending"
        assert res.all_acquisitions[0].relative_orbit == 59
        assert res.all_acquisitions[0].mode == "IW"
        assert res.all_acquisitions[0].polarizations == ["VV", "VH"]
        
        # Test acquisition_dates is present and accurate
        assert res.acquisition_dates == ("2024-01-01", "2024-03-01")
        
        assert res.result.t1_acquisition.scene_id == "scene_1"
        assert res.result.t2_acquisition.scene_id == "scene_3"
