import pytest
from unittest import mock
import os

from src.api.routers.detect import router
from fastapi.testclient import TestClient
from fastapi import FastAPI
from src.data_ingestion.optical_client import fetch_optical_basemap
from src.data_ingestion.sentinel_client import CDSEAuthManager
import src.api.db as db

app = FastAPI()
app.include_router(router)
client = TestClient(app)

@mock.patch("src.api.routers.detect.fetch_optical_basemap")
@mock.patch("src.api.routers.detect.load_sar_pair_for_inference")
@mock.patch("src.storage.object_storage.download_bytes")
@mock.patch("src.api.routers.detect.run_change_detection")
@mock.patch("src.api.routers.detect._get_or_create_scene")
@mock.patch("src.api.routers.detect.db")
def test_metrics_recorded_on_storage_hit(
    mock_db,
    mock_get_or_create_scene,
    mock_run_change_detection,
    mock_download_bytes,
    mock_load_sar_pair,
    mock_optical_basemap
):
    """
    Test that total_ms, optical_fetch_ms, reprojection_ms, download_ms etc.
    are successfully aggregated into job.metrics.
    """
    # 1. Setup mock database
    mock_session = mock.Mock()
    # Support `with SessionLocal() as session:`
    mock_session.__enter__ = mock.Mock(return_value=mock_session)
    mock_session.__exit__ = mock.Mock(return_value=None)
        
    jobs = []
    def mock_add(obj):
        if hasattr(obj, 'id') and getattr(obj, 'id') is None:
            obj.id = 1
            if type(obj).__name__ == "ChangeDetectionJob":
                jobs.append(obj)
            
    mock_session.add.side_effect = mock_add
    mock_db.SessionLocal.return_value = mock_session

    mock_session.query.return_value.get.side_effect = lambda id: jobs[0] if jobs else None
    
    # Fake SAR asset query returning valid assets
    mock_asset = mock.Mock()
    mock_asset.storage_key = "fake_key"
    mock_session.query.return_value.filter_by.return_value.first.return_value = mock_asset

    # 2. Setup mock inference logic
    from src.api.services.inference_service import InferenceResult
    mock_result = InferenceResult(
        change_percentage=10.0,
        mean_change_probability=0.8,
        total_pixels=1000,
        changed_pixels=100,
        total_changed_area_sq_km=0.5,
        num_change_clusters=1,
        regions=[],
        t1_preview_base64="",
        t2_preview_base64="",
        t1_grayscale_base64="",
        t2_grayscale_base64="",
        t1_false_color_base64="",
        t2_false_color_base64="",
        change_mask_base64="",
        confidence_heatmap_base64="",
        overlay_base64="",
        change_boxes_base64="",
        model_inference_ms=120.0,
        postprocessing_ms=10.0,
    )
    mock_run_change_detection.return_value = mock_result
    
    # 3. Setup optical basemap return
    # image_array, fetch_ms, reproject_ms
    mock_optical_basemap.return_value = (None, 45.0, 5.0)
    
    # Setup load_sar_pair
    t1_np_mock = mock.Mock()
    t1_np_mock.shape = (3, 50, 50)
    t2_np_mock = mock.Mock()
    t2_np_mock.shape = (3, 50, 50)
    mock_load_sar_pair.return_value = (t1_np_mock, t2_np_mock)

    with mock.patch("src.data_ingestion.sentinel_client.SentinelHubClient") as mock_client:
        mock_client_inst = mock.Mock()
        mock_client_inst.fetch_scene_metadata.return_value = {
            "provider": "copernicus",
            "scene_id": "fake_id",
            "acquisition_date": "2023-01-01T00:00:00Z",
            "raster_metadata": {"transform": None, "crs": None}
        }
        mock_client.return_value = mock_client_inst
        
        with mock.patch("src.data_ingestion.sentinel_client.CDSEAuthManager"):
            with mock.patch("src.preprocessing.sar_loader.extract_geotiff_metadata") as mock_extract:
                mock_extract.return_value = {"transform": None, "crs": None}
                
                res = client.post("/detect/sentinel", json={
                    "bbox": {"min_lon": 10.0, "min_lat": 45.0, "max_lon": 10.1, "max_lat": 45.1},
                    "date_range_t1": ["2023-01-01", "2023-01-10"],
                    "date_range_t2": ["2023-02-01", "2023-02-10"]
                })

    assert res.status_code == 200, res.json()
    
    # Check that jobs[0].metrics was updated
    metrics = jobs[0].metrics
    assert "total_ms" in metrics
    assert "optical_fetch_ms" in metrics
    assert "reprojection_ms" in metrics
    assert "download_ms" in metrics
    assert "preprocessing_ms" in metrics
    assert "metadata_extraction_ms" in metrics
    assert "model_inference_ms" in metrics
    assert "postprocessing_ms" in metrics
    
    assert metrics["optical_fetch_ms"] == 45.0
    assert metrics["reprojection_ms"] == 5.0
    assert metrics["model_inference_ms"] == 120.0
    assert metrics["postprocessing_ms"] == 10.0
    assert metrics["total_ms"] > 0
    assert metrics["download_ms"] >= 0

@mock.patch("requests.post")
def test_cdse_timeout_config(mock_post):
    """
    Test that CDSE explicit timeouts are passed through from env vars.
    """
    os.environ["CDSE_CONNECT_TIMEOUT_SEC"] = "15"
    os.environ["CDSE_READ_TIMEOUT_SEC"] = "45"
    
    auth = CDSEAuthManager(client_id="fake", client_secret="fake")
    
    # Set up mock response
    mock_resp = mock.Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"access_token": "token", "expires_in": 3600}
    mock_post.return_value = mock_resp
    
    auth.get_token()
    
    # Assert requests.post was called with timeout=(15, 45)
    mock_post.assert_called_with(
        mock.ANY,
        data=mock.ANY,
        timeout=(15, 45)
    )

@mock.patch("src.data_ingestion.optical_client.requests.get")
def test_optical_timeout_config(mock_get):
    """
    Test that Optical explicitly enforces timeout from env var.
    """
    os.environ["OPTICAL_TIMEOUT_SEC"] = "12"
    
    mock_resp = mock.Mock()
    mock_resp.status_code = 400
    mock_get.return_value = mock_resp
    
    fetch_optical_basemap([0,0,1,1], (100, 100))
    
    mock_get.assert_called_with(
        mock.ANY,
        params=mock.ANY,
        timeout=12
    )
