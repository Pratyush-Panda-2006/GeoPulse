import numpy as np
import pytest
from PIL import Image

from src.api.services.vision_encoder import (
    _robust_scale_pair,
    sar_pair_to_rgb,
    build_side_by_side_image,
    encode_jpeg,
)


def test_shared_robust_scale_returns_matching_shapes():
    t1 = np.linspace(0.0, 1.0, 100, dtype=np.float32).reshape(10, 10)
    t2 = np.linspace(0.2, 0.8, 100, dtype=np.float32).reshape(10, 10)

    t1_scaled, t2_scaled = _robust_scale_pair(t1, t2)

    assert t1_scaled.shape == t1.shape
    assert t2_scaled.shape == t2.shape
    assert t1_scaled.dtype == np.float32
    assert t2_scaled.dtype == np.float32

    assert np.all(t1_scaled >= 0.0)
    assert np.all(t1_scaled <= 1.0)
    assert np.all(t2_scaled >= 0.0)
    assert np.all(t2_scaled <= 1.0)


def test_sar_pair_to_rgb_shape_and_dtype():
    rng = np.random.default_rng(42)

    t1 = rng.random((2, 40, 50), dtype=np.float32)
    t2 = rng.random((2, 40, 50), dtype=np.float32)

    t1_rgb, t2_rgb = sar_pair_to_rgb(t1, t2)

    assert t1_rgb.shape == (40, 50, 3)
    assert t2_rgb.shape == (40, 50, 3)

    assert t1_rgb.dtype == np.uint8
    assert t2_rgb.dtype == np.uint8

    assert t1_rgb.min() >= 0
    assert t1_rgb.max() <= 255
    assert t2_rgb.min() >= 0
    assert t2_rgb.max() <= 255


def test_t1_t2_spatial_dimensions_must_match():
    t1 = np.zeros((2, 40, 50), dtype=np.float32)
    t2 = np.zeros((2, 41, 50), dtype=np.float32)

    with pytest.raises(ValueError):
        sar_pair_to_rgb(t1, t2)


def test_sar_arrays_must_have_two_bands():
    t1 = np.zeros((3, 40, 50), dtype=np.float32)
    t2 = np.zeros((2, 40, 50), dtype=np.float32)

    with pytest.raises(ValueError):
        sar_pair_to_rgb(t1, t2)


def test_side_by_side_width_is_doubled():
    t1_rgb = np.zeros((30, 40, 3), dtype=np.uint8)
    t2_rgb = np.ones((30, 40, 3), dtype=np.uint8) * 255

    combined = build_side_by_side_image(t1_rgb, t2_rgb)

    assert combined.shape == (30, 80, 3)
    assert combined.dtype == np.uint8

    # Left half must remain T1.
    assert np.all(combined[:, :40] == 0)

    # Right half must remain T2.
    assert np.all(combined[:, 40:] == 255)


def test_side_by_side_requires_matching_images():
    t1_rgb = np.zeros((30, 40, 3), dtype=np.uint8)
    t2_rgb = np.zeros((31, 40, 3), dtype=np.uint8)

    with pytest.raises(ValueError):
        build_side_by_side_image(t1_rgb, t2_rgb)


def test_jpeg_encoding_produces_valid_image():
    image = np.zeros((32, 48, 3), dtype=np.uint8)
    image[:, :, 0] = 255

    jpeg_bytes = encode_jpeg(image, quality=90)

    assert isinstance(jpeg_bytes, bytes)
    assert len(jpeg_bytes) > 0

    decoded = Image.open(__import__("io").BytesIO(jpeg_bytes))

    assert decoded.format == "JPEG"
    assert decoded.size == (48, 32)
    assert decoded.mode == "RGB"


def test_jpeg_rejects_non_uint8():
    image = np.zeros((32, 48, 3), dtype=np.float32)

    with pytest.raises(ValueError):
        encode_jpeg(image)


def test_nan_and_inf_are_handled():
    t1 = np.zeros((2, 20, 20), dtype=np.float32)
    t2 = np.zeros((2, 20, 20), dtype=np.float32)

    t1[0, 5, 5] = np.nan
    t1[1, 6, 6] = np.inf
    t2[0, 7, 7] = -np.inf

    t1_rgb, t2_rgb = sar_pair_to_rgb(t1, t2)

    assert t1_rgb.shape == (20, 20, 3)
    assert t2_rgb.shape == (20, 20, 3)
    assert t1_rgb.dtype == np.uint8
    assert t2_rgb.dtype == np.uint8