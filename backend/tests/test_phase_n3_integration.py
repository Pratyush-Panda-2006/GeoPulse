import pytest
import numpy as np

from src.api.schemas import ChangedRegion
from src.api.services.vision_pipeline import prepare_vision_payload, NemotronPayload

def make_test_arrays():
    """Returns fake (2, 100, 120) T1 and T2 tensors for testing"""
    t1 = np.zeros((2, 100, 120), dtype=np.float32)
    t2 = np.ones((2, 100, 120), dtype=np.float32)
    return t1, t2

def make_region(bbox, severity="High") -> ChangedRegion:
    return ChangedRegion(
        region_id=1,
        area_px=100,
        centroid_xy=(50.0, 50.0),
        bbox_xy=bbox,
        severity=severity
    )

def test_high_region_accepted():
    t1, t2 = make_test_arrays()
    # size 30x30 >= 8x8 (minimum size)
    region = make_region(bbox=(20, 20, 50, 50), severity="High")
    payload = prepare_vision_payload(t1, t2, region)
    
    assert payload.status == "ready"
    assert payload.jpeg_bytes is not None
    assert payload.crop_bbox is not None
    # Validate no coordinate reprojection: outputs are clamped pixel boundaries
    # row: max(0, 20-32) = 0, min(100, 50+32) = 82
    # col: max(0, 20-32) = 0, min(120, 50+32) = 82
    assert payload.crop_bbox == (0, 0, 82, 82)

def test_non_high_region_skipped():
    t1, t2 = make_test_arrays()
    region = make_region(bbox=(20, 20, 50, 50), severity="Medium")
    payload = prepare_vision_payload(t1, t2, region)
    
    assert payload.status == "skipped_non_high"
    assert payload.jpeg_bytes is None
    assert payload.crop_bbox is None

def test_too_small_high_region_skipped():
    t1, t2 = make_test_arrays()
    # size 5x5 < 8x8 (minimum size)
    region = make_region(bbox=(20, 20, 25, 25), severity="High")
    payload = prepare_vision_payload(t1, t2, region)
    
    assert payload.status == "skipped_small_crop"
    assert payload.jpeg_bytes is None
    assert payload.crop_bbox is None

def test_resulting_bytes_are_valid_jpeg():
    t1, t2 = make_test_arrays()
    region = make_region(bbox=(20, 20, 50, 50), severity="High")
    payload = prepare_vision_payload(t1, t2, region)
    
    # Valid JPEG magic bytes start with FF D8
    assert payload.jpeg_bytes.startswith(b'\xff\xd8')

def test_bbox_passed_through_correctly():
    t1, t2 = make_test_arrays()
    # Check another size explicitly to ensure bbox padding behaves predictably
    region = make_region(bbox=(40, 40, 60, 60), severity="High")
    payload = prepare_vision_payload(t1, t2, region)
    
    assert payload.status == "ready"
    # min_row=40-32=8, min_col=40-32=8
    # max_row=60+32=92, max_col=60+32=92
    assert payload.crop_bbox == (8, 8, 92, 92)
