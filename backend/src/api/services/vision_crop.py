"""
NVIDIA Nemotron vision crop utilities.

Phase N3:
- Extract aligned T1/T2 crops from the same pixel grid used by Model 3.
- Add configurable padding around a detected region.
- Keep crop coordinates in the model raster pixel space.
- Never perform geographic coordinate conversion here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np

MIN_REGION_WIDTH_PX = 8
MIN_REGION_HEIGHT_PX = 8


@dataclass(frozen=True)
class VisionCrop:
    """
    A synchronized T1/T2 crop from the Model 3 raster grid.

    Coordinates use NumPy image convention:
        row = y
        col = x

    bbox is:
        (min_row, min_col, max_row, max_col)

    max_row and max_col are exclusive.
    """

    t1: np.ndarray
    t2: np.ndarray

    bbox: Tuple[int, int, int, int]

    original_bbox: Tuple[int, int, int, int]

    padding_px: int


def _validate_bbox(
    bbox: Tuple[int, int, int, int],
    height: int,
    width: int,
) -> None:
    """Validate a Model 3 pixel-space bounding box."""

    if len(bbox) != 4:
        raise ValueError("bbox must contain exactly 4 values")

    min_row, min_col, max_row, max_col = bbox

    if min_row < 0 or min_col < 0:
        raise ValueError("bbox coordinates cannot be negative")

    if max_row <= min_row or max_col <= min_col:
        raise ValueError(
            "bbox must have positive height and width"
        )

    if max_row > height or max_col > width:
        raise ValueError(
            "bbox extends beyond the image dimensions"
        )


def is_region_large_enough(
    bbox: Tuple[int, int, int, int],
) -> bool:
    """
    Return True when the detected Model 3 region is large enough
    to be considered for visual interpretation.

    The decision uses the original detected region,
    not the padded crop.
    """

    min_row, min_col, max_row, max_col = bbox

    width = max_col - min_col
    height = max_row - min_row

    return (
        width >= MIN_REGION_WIDTH_PX
        and height >= MIN_REGION_HEIGHT_PX
    )


def extract_aligned_crop(
    t1_np: np.ndarray,
    t2_np: np.ndarray,
    bbox: Tuple[int, int, int, int],
    padding_px: int = 32,
) -> VisionCrop:
    """
    Extract synchronized T1/T2 crops using the Model 3 pixel grid.

    Parameters
    ----------
    t1_np, t2_np:
        SAR arrays in (C, H, W) format.

    bbox:
        Model 3 region bounding box:
        (min_row, min_col, max_row, max_col)
        with exclusive max indices.

    padding_px:
        Number of pixels added around the detected region.
        Padding is clipped to image boundaries.

    Returns
    -------
    VisionCrop
        Synchronized T1/T2 crop plus the actual clipped crop bbox.
    """

    if not isinstance(t1_np, np.ndarray) or not isinstance(t2_np, np.ndarray):
        raise TypeError("t1_np and t2_np must be numpy arrays")

    if t1_np.ndim != 3 or t2_np.ndim != 3:
        raise ValueError(
            "t1_np and t2_np must have shape (C, H, W)"
        )

    if t1_np.shape[0] != t2_np.shape[0]:
        raise ValueError(
            "T1 and T2 must have the same number of channels"
        )

    if t1_np.shape[1:] != t2_np.shape[1:]:
        raise ValueError(
            "T1 and T2 must have identical spatial dimensions"
        )

    if not isinstance(padding_px, int) or padding_px < 0:
        raise ValueError(
            "padding_px must be a non-negative integer"
        )

    height, width = t1_np.shape[1:]

    _validate_bbox(bbox, height, width)

    min_row, min_col, max_row, max_col = bbox

    padded_min_row = max(0, min_row - padding_px)
    padded_min_col = max(0, min_col - padding_px)

    padded_max_row = min(height, max_row + padding_px)
    padded_max_col = min(width, max_col + padding_px)

    crop_bbox = (
        padded_min_row,
        padded_min_col,
        padded_max_row,
        padded_max_col,
    )

    t1_crop = t1_np[
        :,
        padded_min_row:padded_max_row,
        padded_min_col:padded_max_col,
    ].copy()

    t2_crop = t2_np[
        :,
        padded_min_row:padded_max_row,
        padded_min_col:padded_max_col,
    ].copy()

    return VisionCrop(
        t1=t1_crop,
        t2=t2_crop,
        bbox=crop_bbox,
        original_bbox=bbox,
        padding_px=padding_px,
    )