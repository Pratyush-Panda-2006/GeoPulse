"""
Tests for Phase 7B: Optical Basemap Reprojection and GeoJSON Vector Detections.
"""

import pytest
import numpy as np
from src.data_ingestion.optical_client import fetch_optical_basemap
from src.api.services.change_analyzer import pixel_to_geo_coords
from unittest import mock
from PIL import Image
import io
from fastapi.testclient import TestClient
from src.api.routers.detect import router
from fastapi import FastAPI
import src.api.db as db

# Setup a mock app for endpoint testing
app = FastAPI()
app.include_router(router)
client = TestClient(app)

class DummyDetection:
    def __init__(self, geometry, properties):
        self.geometry = geometry
        self.properties = properties

class DummyJob:
    def __init__(self, job_id, detections):
        self.id = job_id
        self.detections = detections


def test_optical_basemap_reprojection_skips_pil_resize():
    """
    Test that if target_crs/transform is provided, naive resize is skipped and
    rasterio.warp.reproject is attempted. If it fails, it returns None.
    """
    # Mock requests.get to return a valid optical image.
    valid_img = Image.new("RGB", (100, 100), color="blue")
    buf = io.BytesIO()
    valid_img.save(buf, format="JPEG")
    buf.seek(0)
    
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "image/jpeg"}
    mock_response.content = buf.read()
    
    with mock.patch("requests.get", return_value=mock_response):
        # 1. No target metadata -> return None (due to new logic where no fallback is allowed if geographic alignment is strictly expected, but wait - the new code says: if no target transform is supplied, it logs and returns None)
        arr_none, _, _ = fetch_optical_basemap(
            bbox=[0.0, 0.0, 1.0, 1.0],
            size_hw=(50, 50),
            target_crs=None,
            target_transform=None
        )
        assert arr_none is None, "Should skip and return None when missing transform"

        # 2. Provide invalid/mock transform to trigger rasterio error
        arr_err, _, _ = fetch_optical_basemap(
            bbox=[0.0, 0.0, 1.0, 1.0],
            size_hw=(50, 50),
            target_crs="invalid_crs",
            target_transform="invalid_transform"
        )
        assert arr_err is None, "Should not fallback to PIL resize on reprojection failure"

        # 3. Provide valid transform and ensure it works
        try:
            import rasterio
            from rasterio.crs import CRS
            from rasterio.transform import from_bounds
            
            target_crs = CRS.from_epsg(4326)
            target_transform = from_bounds(0.0, 0.0, 1.0, 1.0, 50, 50)
            
            arr_success, _, _ = fetch_optical_basemap(
                bbox=[0.0, 0.0, 1.0, 1.0],
                size_hw=(50, 50),
                target_crs=target_crs,
                target_transform=target_transform
            )
            assert arr_success is not None
            assert arr_success.shape == (50, 50, 3)
        except ImportError:
            pass


def test_pixel_to_geo_coords_affine():
    """
    Test that real Affine transforms are used instead of linear interpolation.
    Verifies that if CRS is EPSG:4326, coordinates are returned directly.
    Verifies that if CRS is not EPSG:4326, coordinates are properly reprojected to WGS84.
    """
    try:
        from rasterio.transform import from_origin
        from rasterio.crs import CRS
        
        # Test 1: EPSG:4326 (WGS84)
        transform_wgs84 = from_origin(10.0, 20.0, 0.1, 0.1)
        crs_wgs84 = CRS.from_epsg(4326)
        
        # Center of pixel (0, 0) should be 10.05, 19.95
        lon, lat = pixel_to_geo_coords(0, 0, None, (10, 10), transform=transform_wgs84, crs=crs_wgs84)
        
        assert abs(lon - 10.05) < 1e-4
        assert abs(lat - 19.95) < 1e-4
        
        # Test 2: EPSG:3857 (Web Mercator)
        # 0, 0 in Web Mercator is 0, 0 in WGS84
        transform_mercator = from_origin(0.0, 100000.0, 10000.0, 10000.0)
        crs_mercator = CRS.from_epsg(3857)
        
        # Pixel (0,0) center in Web Mercator is x=5000, y=95000
        # WGS84 lon for x=5000 is ~0.0449, lat for y=95000 is ~0.853
        lon2, lat2 = pixel_to_geo_coords(0, 0, None, (10, 10), transform=transform_mercator, crs=crs_mercator)
        
        assert abs(lon2 - 0.044915) < 1e-2
        assert abs(lat2 - 0.85351) < 1e-2
        
    except ImportError:
        pass


@mock.patch("src.api.routers.detect.db")
def test_geojson_endpoint(mock_db):
    """
    Test that the GeoJSON endpoint returns a valid FeatureCollection
    with valid polygon geometries.
    """
    mock_session = mock.Mock()
    mock_db.SessionLocal.return_value = mock_session
    
    # Mock job with detections
    mock_job = DummyJob(
        job_id=1,
        detections=[
            DummyDetection(
                geometry={
                    "type": "Polygon",
                    "coordinates": [
                        [[1.0, 1.0], [2.0, 1.0], [2.0, 2.0], [1.0, 2.0], [1.0, 1.0]]
                    ]
                },
                properties={
                    "region_id": 1,
                    "severity": "High",
                    "mean_change_prob": 0.85,
                    "approx_area_sq_km": 1.5,
                }
            ),
            # Invalid/empty detection geometry
            DummyDetection(
                geometry=None,
                properties={"severity": "Low"}
            )
        ]
    )
    
    mock_session.query.return_value.get.return_value = mock_job
    mock_session.query.return_value.filter.return_value.all.return_value = mock_job.detections
    
    res = client.get("/detect/1/detections.geojson")
    assert res.status_code == 200
    
    data = res.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 1 # Only one valid geometry
    
    feat = data["features"][0]
    assert feat["type"] == "Feature"
    assert feat["geometry"]["type"] == "Polygon"
    assert feat["geometry"]["coordinates"][0][0] == [1.0, 1.0] # Closed ring check
    assert feat["geometry"]["coordinates"][0][-1] == [1.0, 1.0]
    assert "geometry" in feat
    
    props = feat["properties"]
    assert props["severity"] == "High"
    
    # Verify Phase 7 Canonical Vector properties
    assert props["region_id"] == 1
    assert props["class"] == "change"
    assert props["confidence"] == 0.85
    assert props["area_sq_km"] == 1.5
    
    # Ensure backward compatibility field remains
    assert props["mean_change_prob"] == 0.85
