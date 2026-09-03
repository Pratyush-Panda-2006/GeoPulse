import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import datetime as dt
import numpy as np

from src.api.main import app

client = TestClient(app)

@pytest.fixture
def mock_cdse_client():
    with patch("src.api.services.analyze_service.SentinelHubClient") as mock_sh_client:
        mock_instance = MagicMock()
        mock_sh_client.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_sar_timeseries():
    with patch("src.api.services.analyze_service.fetch_sar_timeseries") as mock_fetch:
        yield mock_fetch

@pytest.fixture
def mock_dem():
    with patch("src.api.services.analyze_service.process_dem_tile") as mock_dem:
        yield mock_dem

@pytest.fixture
def mock_context_layers():
    with patch("src.api.services.analyze_service.get_weather_context") as mw, \
         patch("src.api.services.context_landcover.get_landcover_context") as mwc, \
         patch("src.api.services.context_fire.get_fire_context") as mf, \
         patch("src.api.services.context_surfacewater.get_surface_water_context") as msw:
        
        mw.return_value = {1: {"endpoint_used": "archive", "total_precipitation_mm": 50, "peak_daily_precipitation_mm": 50, "peak_day": "2024-01-10", "rainfall_class": "HIGH"}}
        mwc.return_value = {1: {"dominant_class": "Trees", "dominant_class_code": 10, "class_histogram": {"10": 100.0}, "is_cropland_dominant": False, "is_tree_consistent": True, "is_sparse_built_consistent": False}}
        mf.return_value = {1: {"nearby": False, "count": 0, "nearest_km": None, "dates": []}}
        msw.return_value = {1: {"new_water_km2": 0.5, "permanent_water_km2": 0.1}}
        yield (mw, mwc, mf, msw)

def test_analyze_endpoint_mocked(mock_sar_timeseries, mock_cdse_client, mock_dem, mock_context_layers):
    # Setup mock returns
    mock_sar_timeseries.return_value = (
        {"images_compared": 2, "intermediate": [], "reason": "test"},
        {"meta": {"scene_id": "S1_old", "acquisition_date": "2024-01-01T00:00:00Z"}, "array": np.zeros((2, 512, 512))},
        {"meta": {"scene_id": "S1_new", "acquisition_date": "2024-01-10T00:00:00Z"}, "array": np.zeros((2, 512, 512))},
        []
    )
    
    mock_cdse_client.fetch_dem_tile.return_value = b"mocked_dem_bytes"
    mock_dem.return_value = {
        1: {"mean_elevation_m": 100.0, "mean_slope_deg": 5.0, "flat": True, "layover_shadow_overlap_pct": 0.0}
    }

    # Execute
    payload = {
        "aoi": {
            "type": "Polygon",
            "coordinates": [[[0,0], [1,0], [1,1], [0,1], [0,0]]]
        },
        "period": {"start": "2024-01-01", "end": "2024-01-31"},
        "mission": "deforestation"
    }

    with patch("src.api.services.analyze_service.run_change_detection") as mock_inference:
        # Mock inference result
        from src.api.schemas import PairwiseChangeResult, ChangedRegion
        mock_inference.return_value = MagicMock(
            regions=[
                ChangedRegion(
                    region_id=1, area_px=100, area_km2=0.5, centroid_xy=(50, 50),
                    bbox_xy=(0,0,10,10), mean_change_prob=0.8, severity="High", label="Change",
                    geo_bbox=(0.1, 0.1, 0.2, 0.2)
                )
            ],
            mean_change_probability=0.8,
            total_changed_area_sq_km=0.5,
            t1_preview_base64=None,
            t2_preview_base64=None,
            t1_grayscale_base64=None,
            t2_grayscale_base64=None,
            t1_false_color_base64=None,
            t2_false_color_base64=None,
            optical_base64=None,
            optical_boxes_base64=None,
            change_mask_base64=None,
            confidence_heatmap_base64=None,
            overlay_base64=None,
            change_boxes_base64=None
        )

        response = client.post("/api/v1/analyze", json=payload)

    # Assertions
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["mission"] == "deforestation"
    assert data["images_compared"] == 2
    assert "t1" in data
    assert "t2" in data
    assert len(data["detections_geojson"]["features"]) == 1
    feature = data["detections_geojson"]["features"][0]
    assert feature["properties"]["region_id"] == 1
    assert "evidence" in feature["properties"]
    assert feature["properties"]["evidence"]["evidence_strength"] in ["LOW", "MEDIUM", "HIGH"]

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main(["-v", __file__]))

