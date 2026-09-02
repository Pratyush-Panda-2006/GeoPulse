import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from src.api.services.context_landcover import get_landcover_context, _fetch_worldcover_window
from src.api.services.evidence_engine import synthesize_evidence
from src.api.schemas import ChangedRegion

def mock_rasterio_open():
    """Mock a rasterio DatasetReader"""
    class MockDataset:
        def __init__(self, arr):
            from affine import Affine
            self.arr = arr
            self.transform = Affine.translation(0, 0)
            
        def read(self, *args, **kwargs):
            return self.arr
            
        def __enter__(self): return self
        def __exit__(self, *args): pass
    return MockDataset

def test_worldcover_window_retrieval_and_caching():
    # 1. Retrieval & 8. Deterministic Caching
    _fetch_worldcover_window.cache_clear()
    
    mock_arr = np.array([[10, 10], [40, 50]])
    with patch("rasterio.open", return_value=mock_rasterio_open()(mock_arr)) as mock_open, \
         patch("rasterio.windows.from_bounds", return_value=MagicMock(width=2, height=2)) as mock_from_bounds:
        arr1 = _fetch_worldcover_window(0.0, 0.0, 1.0, 1.0)
        assert arr1 is not None
        assert arr1.shape == (2, 2)
        assert mock_open.call_count == 1
        
        # Second call should hit cache
        arr2 = _fetch_worldcover_window(0.0, 0.0, 1.0, 1.0)
        assert np.array_equal(arr1, arr2)
        assert mock_open.call_count == 1

def test_worldcover_class_decoding_and_dominant():
    # 2. Class decoding, 3. dominant-class, 4. histogram percentages
    _fetch_worldcover_window.cache_clear()
    # 4 pixels: 2x Cropland (40), 1x Tree (10), 1x Built-up (50)
    mock_arr = np.array([[40, 40], [10, 50]])
    
    region = ChangedRegion(
        region_id=1, area_px=4, centroid_xy=(0.5, 0.5), bbox_xy=(0,0,2,2),
        geo_bbox=(0.0, 0.0, 1.0, 1.0), severity="Medium", label="Change"
    )
    
    with patch("src.api.services.context_landcover._fetch_worldcover_window", return_value=mock_arr):
        ctx = get_landcover_context([region])
        
        assert 1 in ctx
        r1_ctx = ctx[1]
        
        # 3. Dominant class calculation
        assert r1_ctx["dominant_class_code"] == 40
        # 2. Class decoding
        assert r1_ctx["dominant_class"] == "Cropland"
        assert r1_ctx["is_cropland_dominant"] is True
        
        # 4. Histogram percentages
        # Cropland 2/4 = 50%, Tree 1/4 = 25%, Built-up 1/4 = 25%
        hist = r1_ctx["class_histogram"]
        assert hist["Cropland"] == 50.0
        assert hist["Tree cover"] == 25.0
        assert hist["Built-up"] == 25.0

def test_evidence_cropland_downgrade_and_missions():
    # 5. Cropland evidence downgrade
    region = ChangedRegion(
        region_id=1, area_px=10, centroid_xy=(0,0), bbox_xy=(0,0,1,1),
        mean_change_prob=0.8, severity="Medium", label="Change"
    )
    landcover_ctx_crop = {
        "dominant_class": "Cropland",
        "dominant_class_code": 40,
        "class_histogram": {},
        "is_cropland_dominant": True,
        "is_tree_consistent": False,
        "is_sparse_built_consistent": False
    }
    
    evidence_crop = synthesize_evidence(region, landcover_context=landcover_ctx_crop)
    # Check if cropland penalty applied
    assert any("Possible agricultural/seasonal surface change" in cav for cav in evidence_crop.caveats)
    assert any(sig.name == "cropland_seasonal_risk" for sig in evidence_crop.signals)
    
    # 6. Forest/mining mission context
    landcover_ctx_water = {
        "dominant_class": "Permanent water bodies",
        "dominant_class_code": 80,
        "class_histogram": {},
        "is_cropland_dominant": False,
        "is_tree_consistent": False,
        "is_sparse_built_consistent": False
    }
    evidence_forest = synthesize_evidence(
        region, 
        landcover_context=landcover_ctx_water, 
        mission_config={"name": "Deforestation"}
    )
    assert any("not consistent with expected tree-cover" in cav for cav in evidence_forest.caveats)
    
    evidence_mining = synthesize_evidence(
        region, 
        landcover_context=landcover_ctx_water, 
        mission_config={"name": "Illegal Mining"}
    )
    assert any("not consistent with bare/sparse or built-up" in cav for cav in evidence_mining.caveats)

def test_worldcover_graceful_failure():
    # 7. Graceful failure
    _fetch_worldcover_window.cache_clear()
    region = ChangedRegion(
        region_id=1, area_px=4, centroid_xy=(0,0), bbox_xy=(0,0,2,2),
        geo_bbox=(0.0, 0.0, 1.0, 1.0), severity="Medium", label="Change"
    )
    
    # Force rasterio.open to fail
    with patch("rasterio.open", side_effect=Exception("S3 bucket down")):
        ctx = get_landcover_context([region])
        assert ctx == {} # Graceful failure, returns empty dict for region
        
        evidence = synthesize_evidence(region, landcover_context=None)
        assert evidence.context.landcover is None
