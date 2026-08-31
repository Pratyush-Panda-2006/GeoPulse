import numpy as np
import pytest
from src.api.services.visualization import sar_to_colorized, sar_to_grayscale

def test_deterministic_output():
    rng = np.random.RandomState(42)
    # Generate some random SAR-like data (2, H, W)
    arr = rng.uniform(0.0, 1.0, size=(2, 64, 64)).astype(np.float32)
    
    out1 = sar_to_colorized(arr)
    out2 = sar_to_colorized(arr)
    
    np.testing.assert_array_equal(out1, out2)

def test_different_distributions_adaptive_palette():
    # Desert-like (low VH compared to VV)
    arr_desert = np.zeros((2, 32, 32), dtype=np.float32)
    arr_desert[0] = 0.8  # High VV
    arr_desert[1] = 0.1  # Low VH
    out_desert = sar_to_colorized(arr_desert)
    
    # Forest-like (high VH compared to VV)
    arr_forest = np.zeros((2, 32, 32), dtype=np.float32)
    arr_forest[0] = 0.6  # Mid VV
    arr_forest[1] = 0.5  # High VH
    out_forest = sar_to_colorized(arr_forest)
    
    # They shouldn't be identically colored
    assert not np.array_equal(out_desert, out_forest)

def test_nodata_remains_black():
    arr = np.ones((2, 32, 32), dtype=np.float32)
    # Inject nodata (0.0) at the center
    arr[:, 10:20, 10:20] = 0.0
    
    out = sar_to_colorized(arr)
    
    # Center should be strictly 0, 0, 0
    nodata_region = out[10:20, 10:20, :]
    assert np.all(nodata_region == 0)
    
    # The rest should not be all zeros
    valid_region = out[0:5, 0:5, :]
    assert np.any(valid_region > 0)

def test_input_array_unchanged():
    rng = np.random.RandomState(42)
    arr = rng.uniform(0.0, 1.0, size=(2, 32, 32)).astype(np.float32)
    arr_copy = arr.copy()
    
    _ = sar_to_colorized(arr)
    
    np.testing.assert_array_equal(arr, arr_copy)

def test_flat_degenerate_images_no_crash():
    # All zeros
    arr_zeros = np.zeros((2, 32, 32), dtype=np.float32)
    out1 = sar_to_colorized(arr_zeros)
    assert out1.shape == (32, 32, 3)
    
    # All ones
    arr_ones = np.ones((2, 32, 32), dtype=np.float32)
    out2 = sar_to_colorized(arr_ones)
    assert out2.shape == (32, 32, 3)
    
    # NaNs
    arr_nans = np.full((2, 32, 32), np.nan, dtype=np.float32)
    out3 = sar_to_colorized(arr_nans)
    assert out3.shape == (32, 32, 3)
