import numpy as np
import pytest

from src.api.services.vision_crop import (
    extract_aligned_crop,
    is_region_large_enough,
)


def make_test_arrays():
    """
    Create deterministic fake SAR arrays:
    (C, H, W) = (2, 100, 120)
    """
    t1 = np.zeros((2, 100, 120), dtype=np.float32)
    t2 = np.ones((2, 100, 120), dtype=np.float32)

    return t1, t2


def test_basic_crop_with_padding():
    t1, t2 = make_test_arrays()

    crop = extract_aligned_crop(
        t1,
        t2,
        bbox=(40, 50, 60, 70),
        padding_px=10,
    )

    assert crop.original_bbox == (40, 50, 60, 70)
    assert crop.bbox == (30, 40, 70, 80)

    assert crop.t1.shape == (2, 40, 40)
    assert crop.t2.shape == (2, 40, 40)


def test_padding_is_clipped_at_image_edges():
    t1, t2 = make_test_arrays()

    crop = extract_aligned_crop(
        t1,
        t2,
        bbox=(0, 0, 10, 12),
        padding_px=20,
    )

    assert crop.bbox == (0, 0, 30, 32)
    assert crop.t1.shape == (2, 30, 32)
    assert crop.t2.shape == (2, 30, 32)


def test_t1_and_t2_are_spatially_synchronized():
    t1, t2 = make_test_arrays()

    crop = extract_aligned_crop(
        t1,
        t2,
        bbox=(25, 30, 50, 55),
        padding_px=5,
    )

    assert crop.t1.shape == crop.t2.shape
    assert crop.t1.shape[1:] == (35, 35)


def test_original_arrays_are_not_modified():
    t1, t2 = make_test_arrays()

    t1_before = t1.copy()
    t2_before = t2.copy()

    extract_aligned_crop(
        t1,
        t2,
        bbox=(25, 30, 50, 55),
        padding_px=5,
    )

    np.testing.assert_array_equal(t1, t1_before)
    np.testing.assert_array_equal(t2, t2_before)


def test_invalid_bbox_rejected():
    t1, t2 = make_test_arrays()

    invalid_boxes = [
        (-1, 10, 20, 30),
        (10, -1, 20, 30),
        (20, 30, 20, 40),
        (20, 30, 25, 30),
        (90, 110, 101, 120),
        (90, 110, 95, 121),
    ]

    for bbox in invalid_boxes:
        with pytest.raises(ValueError):
            extract_aligned_crop(
                t1,
                t2,
                bbox=bbox,
                padding_px=5,
            )


def test_invalid_padding_rejected():
    t1, t2 = make_test_arrays()

    with pytest.raises(ValueError):
        extract_aligned_crop(
            t1,
            t2,
            bbox=(20, 20, 40, 40),
            padding_px=-1,
        )


def test_mismatched_spatial_dimensions_rejected():
    t1 = np.zeros((2, 100, 120), dtype=np.float32)
    t2 = np.ones((2, 101, 120), dtype=np.float32)

    with pytest.raises(ValueError):
        extract_aligned_crop(
            t1,
            t2,
            bbox=(20, 20, 40, 40),
            padding_px=5,
        )


def test_wrong_array_shape_rejected():
    t1 = np.zeros((100, 120), dtype=np.float32)
    t2 = np.ones((2, 100, 120), dtype=np.float32)

    with pytest.raises(ValueError):
        extract_aligned_crop(
            t1,
            t2,
            bbox=(20, 20, 40, 40),
            padding_px=5,
        )


def test_crop_contains_expected_source_pixels():
    t1, t2 = make_test_arrays()

    # Put a known marker at the expected crop origin.
    t1[0, 30, 40] = 123.0
    t2[1, 30, 40] = 456.0

    crop = extract_aligned_crop(
        t1,
        t2,
        bbox=(40, 50, 60, 70),
        padding_px=10,
    )

    # Source (30,40) becomes crop (0,0).
    assert crop.t1[0, 0, 0] == 123.0
    assert crop.t2[1, 0, 0] == 456.0


def test_region_large_enough():
    assert is_region_large_enough(
        (20, 30, 28, 38)
    ) is True


def test_region_too_narrow():
    assert is_region_large_enough(
        (20, 30, 28, 37)
    ) is False


def test_region_too_short():
    assert is_region_large_enough(
        (20, 30, 27, 38)
    ) is False


def test_region_below_both_dimensions():
    assert is_region_large_enough(
        (20, 30, 27, 37)
    ) is False


def test_region_exact_minimum_size():
    assert is_region_large_enough(
        (20, 30, 28, 38)
    ) is True