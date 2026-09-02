import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from src.api.services.context_surfacewater import get_surface_water_context, _calculate_equal_area_km2, _fetch_jrc_water_window
from src.api.services.evidence_engine import synthesize_evidence
from src.api.schemas import ChangedRegion
import rasterio

def test_otsu_and_synthetic_dark_water():
    # 1. Otsu thresholding
    # 3. synthetic dark-water patch
    
    # Create a synthetic 100x100 array with a dark water patch
    t2_array = np.ones((1, 100, 100), dtype=np.float32) * 0.2
    t2_array[0, 20:40, 20:40] = 0.01 # Dark water patch
    
    region = ChangedRegion(
        region_id=1, area_px=400, bbox_xy=(0,0,100,100), centroid_xy=(0,0),
        geo_centroid=(0.0, 0.0), geo_bbox=(0.0, 0.0, 0.01, 0.01),
        mean_change_prob=0.8, severity="High", label="Change"
    )
    
    with patch('src.api.services.context_surfacewater._fetch_jrc_water_window', return_value=(None, None)):
        ctx = get_surface_water_context([region], t2_array, [0,0,0.01,0.01], {})
        
        assert 1 in ctx
        assert ctx[1]["new_water_km2"] > 0
        assert ctx[1]["permanent_water_km2"] == 0

def test_fixed_threshold_fallback():
    # 2. fixed-threshold fallback
    # If the array is uniform, Otsu fails.
    t2_array = np.ones((1, 100, 100), dtype=np.float32) * 0.03 # All dark water
    
    region = ChangedRegion(
        region_id=1, area_px=400, bbox_xy=(0,0,100,100), centroid_xy=(0,0),
        geo_centroid=(0.0, 0.0), geo_bbox=(0.0, 0.0, 0.01, 0.01),
        mean_change_prob=0.8, severity="High", label="Change"
    )
    
    with patch('src.api.services.context_surfacewater._fetch_jrc_water_window', return_value=(None, None)):
        ctx = get_surface_water_context([region], t2_array, [0,0,0.01,0.01], {})
        
        assert 1 in ctx
        # With fixed fallback (0.05), the 0.03 array is all water.
        assert ctx[1]["new_water_km2"] > 0
        
def test_permanent_water_removal():
    # 4. permanent-water removal
    # 5. new-water-area calculation
    # 8. cache behavior
    
    t2_array = np.ones((1, 100, 100), dtype=np.float32) * 0.2
    t2_array[0, 10:50, 10:50] = 0.01 # Water detected by SAR
    
    # JRC permanent water is present in a subset of the detected water
    jrc_data = np.zeros((100, 100), dtype=np.uint8)
    jrc_data[10:30, 10:50] = 100 # Permanent water (>80%)
    
    region = ChangedRegion(
        region_id=1, area_px=1600, bbox_xy=(0,0,100,100), centroid_xy=(0,0),
        geo_centroid=(0.0, 0.0), geo_bbox=(0.0, 0.0, 0.01, 0.01),
        mean_change_prob=0.8, severity="High", label="Change"
    )
    
    with patch('src.api.services.context_surfacewater._fetch_jrc_water_window', return_value=(jrc_data, rasterio.Affine.identity())):
        ctx = get_surface_water_context([region], t2_array, [0,0,0.01,0.01], {})
        
        assert 1 in ctx
        assert ctx[1]["permanent_water_km2"] > 0
        assert ctx[1]["new_water_km2"] > 0
        
def test_graceful_failure():
    # 7. graceful failure
    t2_array = np.ones((1, 100, 100), dtype=np.float32)
    
    region = ChangedRegion(
        region_id=1, area_px=400, bbox_xy=(0,0,100,100), centroid_xy=(0,0),
        geo_centroid=(0.0, 0.0), geo_bbox=(0.0, 0.0, 0.01, 0.01),
        mean_change_prob=0.8, severity="High", label="Change"
    )
    
    # JRC failure
    _fetch_jrc_water_window.cache_clear()
    with patch('src.api.services.context_surfacewater.rasterio.open', side_effect=Exception("Timeout")):
        ctx = get_surface_water_context([region], t2_array, [0,0,0.01,0.01], {})
        assert 1 in ctx
        # Should proceed smoothly without permanent water mask
        assert ctx[1]["new_water_km2"] == 0
        
    # T2 failure (t2_array is None)
    ctx = get_surface_water_context([region], None, [0,0,0.01,0.01], {})
    assert ctx == {}
    
def test_equal_area_calculation():
    # 6. equal-area area calculation
    mask = np.ones((10, 10), dtype=bool)
    # Simple transform representing 0.0001 deg per pixel at equator
    transform = rasterio.Affine(0.0001, 0.0, 0.0, 0.0, -0.0001, 0.0)
    
    area = _calculate_equal_area_km2(mask, transform)
    # 10x10 = 100 pixels. At equator, 0.0001 deg ~ 11.1m. 100 * (11.1)^2 ~ 12300 m2 = 0.0123 km2
    assert area > 0.01

def test_evidence_engine_integration():
    # 11. EvidenceObject receives surface water context without changing Model 3 detections
    region = ChangedRegion(
        region_id=1, area_px=4, centroid_xy=(0,0), bbox_xy=(0,0,1,1),
        geo_centroid=(0.0, 0.0), mean_change_prob=0.85, severity="Medium", label="Change"
    )
    
    sw_ctx = {
        "new_water_km2": 0.5,
        "permanent_water_km2": 0.1
    }
    
    ev_before = synthesize_evidence(region, surface_water_context=None)
    sar_sig_before = next(s for s in ev_before.signals if s.name == "sar_backscatter_anomaly")
    
    ev_after = synthesize_evidence(region, surface_water_context=sw_ctx)
    sar_sig_after = next(s for s in ev_after.signals if s.name == "sar_backscatter_anomaly")
    sw_sig_after = next((s for s in ev_after.signals if s.name == "new_surface_water_detected"), None)
    
    assert sar_sig_before.value == sar_sig_after.value == 0.85
    assert sw_sig_after is not None
    assert sw_sig_after.value == 0.5
    assert ev_after.context.surface_water.model_dump() == sw_ctx
