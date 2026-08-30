import io
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import numpy as np
import torch
import warnings
from PIL import Image

# Ignore Pydantic V2 warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

from src.api.main import app
from src.api.services.model_service import ModelService
from src.api.services.change_analyzer import extract_changed_regions, pixel_to_geo_coords

client = TestClient(app)

def test_health_no_random_models():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "snunet_cd_sar" in data["loaded_models"]
    assert "siamese_unet_sar" not in data["loaded_models"]
    assert "siamese_unet_rgb" not in data["loaded_models"]
    assert "snunet_cd" not in data["loaded_models"]

def test_models_no_random_models():
    response = client.get("/api/v1/models")
    assert response.status_code == 200
    data = response.json()
    models = [m["name"] for m in data]
    assert "snunet_cd_sar" in models
    assert len(models) == 1

def test_detect_sentinel_refuses_untrained_model():
    req_data = {
        "bbox": {"min_lon": 0, "min_lat": 0, "max_lon": 1, "max_lat": 1},
        "date_range_t1": ["2024-01-01", "2024-01-10"],
        "date_range_t2": ["2024-02-01", "2024-02-10"],
        "model_name": "siamese_unet",  # Explicitly request untrained
        "threshold": 0.5,
        "min_region_area_px": 10
    }
    response = client.post("/api/v1/detect/sentinel", json=req_data)
    assert response.status_code == 400
    assert "not allowed or has no trained checkpoint" in response.text

def test_detect_upload_refuses_untrained_model():
    img_bytes = io.BytesIO()
    Image.new('RGB', (16, 16)).save(img_bytes, format='PNG')
    files = {
        "image_t1": ("t1.png", img_bytes.getvalue(), "image/png"),
        "image_t2": ("t2.png", img_bytes.getvalue(), "image/png"),
    }
    data = {"model_name": "siamese_unet_rgb"}
    response = client.post("/api/v1/detect/upload", files=files, data=data)
    assert response.status_code == 400
    assert "not allowed or has no trained checkpoint" in response.text

from src.api.services.inference_service import InferenceResult
@patch("src.api.routers.detect.fetch_optical_basemap")
@patch("src.api.routers.detect.run_change_detection")
@patch("src.api.routers.detect.load_sar_pair_for_inference")
@patch("src.storage.object_storage.download_bytes")
@patch("src.api.routers.detect._get_or_create_scene")
@patch("src.data_ingestion.sentinel_client.SentinelHubClient.fetch_scene_metadata")
@patch("src.api.routers.detect.db")
def test_detect_sentinel_with_trained_model(
    mock_db, mock_fetch_meta, mock_get_scene, mock_download, mock_load, mock_run, mock_opt
):
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=None)
    mock_db.SessionLocal.return_value = mock_session

    # Force storage reuse path by making the query return a mock asset
    mock_asset = MagicMock()
    mock_asset.storage_key = "fake_key"
    mock_session.query.return_value.filter_by.return_value.first.return_value = mock_asset

    mock_fetch_meta.return_value = {"id": "fake_scene", "acquisition_date": "2024-01-01T00:00:00Z"}
    mock_get_scene.return_value = MagicMock(id=1)
    mock_download.return_value = b"fake_bytes"
    mock_load.return_value = (np.zeros((2, 16, 16), dtype=np.float32), np.zeros((2, 16, 16), dtype=np.float32))
    
    mock_run.return_value = InferenceResult(
        change_percentage=10.0,
        t1_preview_base64="b64", t2_preview_base64="b64",
        t1_grayscale_base64="b64", t2_grayscale_base64="b64",
        t1_false_color_base64="b64", t2_false_color_base64="b64",
        change_mask_base64="b64", confidence_heatmap_base64="b64",
        overlay_base64="b64", change_boxes_base64="b64",
        total_pixels=256, changed_pixels=25, num_change_clusters=1,
        total_changed_area_sq_km=None, regions=[], mean_change_probability=0.9,
        model_inference_ms=0.0, postprocessing_ms=0.0
    )
    mock_opt.return_value = (None, 0.0, 0.0)

    req_data = {
        "bbox": {"min_lon": 0, "min_lat": 0, "max_lon": 1, "max_lat": 1},
        "model_name": "snunet_cd_sar"
    }
    response = client.post("/api/v1/detect/sentinel", json=req_data)
    assert response.status_code == 200, response.text

def test_missing_model_3_checkpoint_refuses_inference():
    svc = ModelService.get_instance()
    # Temporarily remove snunet_cd_sar to simulate missing checkpoint
    original = svc._models.pop("snunet_cd_sar", None)
    
    img_bytes = io.BytesIO()
    Image.new('L', (16, 16)).save(img_bytes, format='PNG')
    files = {
        "image_t1": ("t1.png", img_bytes.getvalue(), "image/png"),
        "image_t2": ("t2.png", img_bytes.getvalue(), "image/png"),
    }
    data = {"model_name": "snunet_cd_sar"}
    response = client.post("/api/v1/detect/upload", files=files, data=data)
    
    # The endpoint should catch ValueError and return 503
    assert response.status_code == 503
    assert "not loaded or has no valid trained checkpoint" in response.text
    
    if original:
        svc._models["snunet_cd_sar"] = original

def test_centroid_synthetic_test():
    # Synthetic binary mask with a square from row 10..20, col 5..15
    binary_mask = np.zeros((100, 100), dtype=np.uint8)
    binary_mask[10:20, 5:15] = 1
    prob_map = np.ones((100, 100), dtype=np.float32) * 0.9
    bbox = [0.0, 0.0, 1.0, 1.0] # min_lon, min_lat, max_lon, max_lat
    
    regions, _ = extract_changed_regions(binary_mask, prob_map, bbox=bbox)
    assert len(regions) == 1
    r = regions[0]
    
    # centroid_xy is (col, row). For [10:20, 5:15], center is approx row=14.5, col=9.5
    assert r.centroid_xy == (9.5, 14.5)
    
    # test geo_centroid extraction
    assert r.geo_centroid is not None
    # X = col/width = 9.5/100 = 0.095 -> lon = 0 + 0.095*1 = 0.095
    # Y = row/height = 14.5/100 = 0.145 -> lat = max_lat - (row/h)*(span) = 1.0 - 0.145 = 0.855
    assert r.geo_centroid[0] == pytest.approx(0.095, abs=0.01)
    assert r.geo_centroid[1] == pytest.approx(0.855, abs=0.01)

def test_repeated_identical_inference_produces_identical_masks():
    svc = ModelService.get_instance()
    t1 = torch.zeros((1, 2, 64, 64), dtype=torch.float32)
    t2 = torch.ones((1, 2, 64, 64), dtype=torch.float32)

    # Assuming snunet_cd_sar is loaded
    if "snunet_cd_sar" in svc._models:
        prob1, mask1 = svc.predict_change_sar(t1, t2, model_name="snunet_cd_sar")
        prob2, mask2 = svc.predict_change_sar(t1, t2, model_name="snunet_cd_sar")
        np.testing.assert_array_equal(mask1, mask2)


def test_sar_to_grayscale_shape_dtype_and_no_input_mutation():
    """Display-only SAR grayscale must return (H, W, 3) uint8 and never mutate
    the input array (which also feeds Model 3 inference)."""
    from src.api.services.visualization import sar_to_grayscale

    rng = np.random.default_rng(0)
    sar = rng.random((2, 48, 40), dtype=np.float32)
    # Include some nodata (0) pixels to exercise the valid-mask branch.
    sar[:, :5, :5] = 0.0
    original = sar.copy()

    out = sar_to_grayscale(sar)

    assert out.shape == (48, 40, 3)
    assert out.dtype == np.uint8
    # Grayscale => all three channels identical.
    np.testing.assert_array_equal(out[..., 0], out[..., 1])
    np.testing.assert_array_equal(out[..., 1], out[..., 2])
    # Input array must be untouched (inference safety invariant).
    np.testing.assert_array_equal(sar, original)


def test_sar_to_colorized_shape_dtype_color_and_no_input_mutation():
    """Colorized 'satellite' SAR must return (H, W, 3) uint8, actually be in
    color (not all-gray), keep nodata black, and never mutate the input."""
    from src.api.services.visualization import sar_to_colorized

    rng = np.random.default_rng(1)
    sar = rng.random((2, 40, 32), dtype=np.float32)
    sar[:, :6, :6] = 0.0  # nodata block
    original = sar.copy()

    out = sar_to_colorized(sar)

    assert out.shape == (40, 32, 3)
    assert out.dtype == np.uint8
    # Nodata pixels must stay black.
    assert np.all(out[:6, :6, :] == 0)
    # Genuinely colored: channels are not all identical across the image.
    assert not (np.array_equal(out[..., 0], out[..., 1]) and np.array_equal(out[..., 1], out[..., 2]))
    # Inference-safety: input untouched.
    np.testing.assert_array_equal(sar, original)


def test_draw_change_boxes_annotates_without_mutating_base():
    """Boxes are baked onto a copy; the base image is not mutated, output shape
    is preserved, and box-colored pixels appear at the region location."""
    from src.api.services.visualization import draw_change_boxes, SEVERITY_COLORS
    from src.api.schemas import ChangedRegion

    base = np.zeros((60, 60, 3), dtype=np.uint8)
    base_copy = base.copy()
    region = ChangedRegion(
        region_id=1, area_px=100, centroid_xy=(30.0, 30.0),
        bbox_xy=(20, 20, 40, 40), mean_change_prob=0.9, severity="Critical",
    )

    out = draw_change_boxes(base, [region], draw_labels=False)

    assert out.shape == (60, 60, 3)
    assert out.dtype == np.uint8
    # Base untouched.
    np.testing.assert_array_equal(base, base_copy)
    # Something was drawn (output differs from the all-black base).
    assert out.sum() > 0
    # The critical box color should be present in the output.
    crit = np.array(SEVERITY_COLORS["Critical"], dtype=np.uint8)
    assert np.any(np.all(out == crit, axis=-1))


def test_draw_change_boxes_empty_regions_is_noop():
    from src.api.services.visualization import draw_change_boxes

    base = (np.ones((20, 20, 3), dtype=np.uint8) * 100)
    out = draw_change_boxes(base, [])
    np.testing.assert_array_equal(out, base)


def test_fetch_optical_basemap_returns_rgb_on_success():
    """With a mocked HTTP image response and provided geospatial metadata, the optical fetcher decodes to an
    (H, W, 3) uint8 array resized to the requested grid via rasterio."""
    from src.data_ingestion import optical_client

    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (10, 120, 30)).save(buf, format="JPEG")
    fake = MagicMock(status_code=200, content=buf.getvalue(),
                     headers={"Content-Type": "image/jpeg"})

    with patch.object(optical_client.requests, "get", return_value=fake):
        # Phase 7: Naive PIL resize without CRS/transform is now disallowed. We must provide
        # real target coordinates to ensure rasterio doesn't skip it and return None.
        import rasterio
        from rasterio.crs import CRS
        from rasterio.transform import from_bounds
        
        target_crs = CRS.from_epsg(4326)
        target_transform = from_bounds(0.0, 0.0, 1.0, 1.0, 48, 40)
        
        out = optical_client.fetch_optical_basemap(
            [0.0, 0.0, 1.0, 1.0], 
            (48, 40),
            target_crs=target_crs,
            target_transform=target_transform
        )

    assert out is not None
    assert isinstance(out, tuple)
    assert len(out) == 3
    arr, _, _ = out
    assert arr is not None
    assert arr.shape == (48, 40, 3)
    assert arr.dtype == np.uint8


def test_fetch_optical_basemap_returns_none_on_failure():
    """Network/provider failures must degrade to None, never raise."""
    from src.data_ingestion import optical_client

    with patch.object(optical_client.requests, "get", side_effect=Exception("no network")):
        out = optical_client.fetch_optical_basemap([0.0, 0.0, 1.0, 1.0], (32, 32))
    assert out == (None, 0.0, 0.0)

    # Non-image (JSON error) response also yields None.
    fake = MagicMock(status_code=200, content=b'{"error":"bad"}',
                     headers={"Content-Type": "application/json"}, text='{"error":"bad"}')
    with patch.object(optical_client.requests, "get", return_value=fake):
        out = optical_client.fetch_optical_basemap([0.0, 0.0, 1.0, 1.0], (32, 32))
    assert out == (None, 0.0, 0.0)


def test_fetch_optical_basemap_disabled_env(monkeypatch):
    from src.data_ingestion import optical_client
    monkeypatch.setenv("OPTICAL_BASEMAP_DISABLED", "1")
    out = optical_client.fetch_optical_basemap([0.0, 0.0, 1.0, 1.0], (32, 32))
    assert out == (None, 0.0, 0.0)



def test_region_merging_overlapping_touching_gap_transitive():
    # 1. Setup a mask with regions
    binary_mask = np.zeros((100, 100), dtype=np.uint8)
    prob_map = np.ones((100, 100), dtype=np.float32) * 0.9

    # Region A: (10, 10) to (20, 20)
    binary_mask[10:20, 10:20] = 1
    
    # Region B: (22, 10) to (30, 20) -> Gap of 2 pixels from A (vertical), should merge
    binary_mask[22:30, 10:20] = 1

    # Region C: (10, 25) to (20, 35) -> Gap of 5 pixels from A (horizontal), should merge
    binary_mask[10:20, 25:35] = 1
    
    # Region D: touching C diagonally -> Gap of 0, should merge
    binary_mask[20:30, 35:45] = 1

    # Region E: (80, 80) to (90, 90) -> Gap of 35+ pixels from D, should NOT merge
    binary_mask[80:90, 80:90] = 1

    regions, _ = extract_changed_regions(binary_mask, prob_map)
    
    # We should have exactly 2 regions:
    # Region 1: Union of A, B, C, D
    # Region 2: E
    
    assert len(regions) == 2, f'Expected 2 regions, got {len(regions)}'
    
    # The merged region should be the largest, so it\'s first
    r_merged = regions[0]
    r_isolated = regions[1]
    
    # Check bounding box of merged region (A, B, C, D)
    # min_row = 10 (A, C)
    # min_col = 10 (A, B)
    # max_row = 30 (B, D)
    # max_col = 45 (D)
    assert r_merged.bbox_xy == (10, 10, 30, 45)
    
    # Check bounding box of isolated region
    assert r_isolated.bbox_xy == (80, 80, 90, 90)
    
    # Check area
    expected_area = (10*10) + (8*10) + (10*10) + (10*10)
    assert r_merged.area_px == expected_area
    assert r_isolated.area_px == 100

def test_region_merging_deterministic_order():
    # Same as above, just ensure multiple runs yield the same result list order
    binary_mask = np.zeros((100, 100), dtype=np.uint8)
    prob_map = np.ones((100, 100), dtype=np.float32) * 0.9
    binary_mask[10:20, 10:20] = 1
    binary_mask[22:30, 10:20] = 1
    binary_mask[10:20, 25:35] = 1
    binary_mask[20:30, 35:45] = 1
    binary_mask[80:90, 80:90] = 1
    
    regions1, _ = extract_changed_regions(binary_mask, prob_map)
    regions2, _ = extract_changed_regions(binary_mask, prob_map)
    
    assert len(regions1) == len(regions2)
    for r1, r2 in zip(regions1, regions2):
        assert r1.region_id == r2.region_id
        assert r1.bbox_xy == r2.bbox_xy
