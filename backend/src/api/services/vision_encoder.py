"""
NVIDIA Nemotron vision encoder.

Phase N3:
- Convert synchronized normalized SAR T1/T2 crops to RGB.
- Use one shared VV/VH intensity normalization across both dates.
- Build a side-by-side before/after image.
- Keep this separate from the existing human-facing visualization pipeline.
"""

from __future__ import annotations

from io import BytesIO
from typing import Tuple

import numpy as np
from PIL import Image


def _robust_scale_pair(
    t1: np.ndarray,
    t2: np.ndarray,
    pmin: float = 2.0,
    pmax: float = 98.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Apply one shared percentile scale to T1 and T2.

    Inputs:
        (H, W) normalized arrays.

    Returns:
        Two float32 arrays in [0, 1].
    """

    combined = np.concatenate(
        [
            t1[np.isfinite(t1)].ravel(),
            t2[np.isfinite(t2)].ravel(),
        ]
    )

    if combined.size == 0:
        return (
            np.zeros_like(t1, dtype=np.float32),
            np.zeros_like(t2, dtype=np.float32),
        )

    lo, hi = np.percentile(combined, (pmin, pmax))

    if hi <= lo:
        return (
            np.clip(t1, 0.0, 1.0).astype(np.float32),
            np.clip(t2, 0.0, 1.0).astype(np.float32),
        )

    t1_scaled = np.clip(
        (t1 - lo) / (hi - lo),
        0.0,
        1.0,
    )

    t2_scaled = np.clip(
        (t2 - lo) / (hi - lo),
        0.0,
        1.0,
    )

    return (
        t1_scaled.astype(np.float32),
        t2_scaled.astype(np.float32),
    )


def sar_pair_to_rgb(
    t1_crop: np.ndarray,
    t2_crop: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Convert synchronized T1/T2 SAR crops to RGB.

    Input:
        T1/T2 shape: (2, H, W)

    Output:
        T1/T2 shape: (H, W, 3), uint8

    Channels:
        R = VV
        G = VH
        B = VV/VH ratio

    The same intensity statistics are used for both dates.
    """

    if t1_crop.ndim != 3 or t2_crop.ndim != 3:
        raise ValueError("T1 and T2 must have shape (2, H, W)")

    if t1_crop.shape[0] != 2 or t2_crop.shape[0] != 2:
        raise ValueError("T1 and T2 must contain exactly VV and VH bands")

    if t1_crop.shape[1:] != t2_crop.shape[1:]:
        raise ValueError("T1 and T2 must have identical spatial dimensions")

    t1 = np.nan_to_num(
        t1_crop.astype(np.float32),
        nan=0.0,
        posinf=1.0,
        neginf=0.0,
    )
    t2 = np.nan_to_num(
        t2_crop.astype(np.float32),
        nan=0.0,
        posinf=1.0,
        neginf=0.0,
    )

    t1 = np.clip(t1, 0.0, 1.0)
    t2 = np.clip(t2, 0.0, 1.0)

    t1_vv, t2_vv = _robust_scale_pair(
        t1[0],
        t2[0],
    )

    t1_vh, t2_vh = _robust_scale_pair(
        t1[1],
        t2[1],
    )

    t1_ratio = np.clip(
        t1[0] / (t1[1] + 0.1),
        0.0,
        3.0,
    ) / 3.0

    t2_ratio = np.clip(
        t2[0] / (t2[1] + 0.1),
        0.0,
        3.0,
    ) / 3.0

    t1_rgb = np.stack(
        [t1_vv, t1_vh, t1_ratio],
        axis=-1,
    )

    t2_rgb = np.stack(
        [t2_vv, t2_vh, t2_ratio],
        axis=-1,
    )

    return (
        np.clip(t1_rgb * 255.0, 0, 255).astype(np.uint8),
        np.clip(t2_rgb * 255.0, 0, 255).astype(np.uint8),
    )


def build_side_by_side_image(
    t1_rgb: np.ndarray,
    t2_rgb: np.ndarray,
) -> np.ndarray:
    """
    Build a simple T1 | T2 RGB image.

    No labels or annotations are added here.
    """

    if t1_rgb.shape != t2_rgb.shape:
        raise ValueError("T1 and T2 RGB images must have identical shapes")

    if t1_rgb.ndim != 3 or t1_rgb.shape[2] != 3:
        raise ValueError("RGB images must have shape (H, W, 3)")

    return np.concatenate(
        [t1_rgb, t2_rgb],
        axis=1,
    ).astype(np.uint8, copy=False)


def encode_jpeg(
    image: np.ndarray,
    quality: int = 90,
) -> bytes:
    """
    Encode an RGB uint8 NumPy image as JPEG bytes.
    """

    if image.dtype != np.uint8:
        raise ValueError("image must have dtype uint8")

    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("image must have shape (H, W, 3)")

    pil_image = Image.fromarray(image, mode="RGB")

    buffer = BytesIO()

    pil_image.save(
        buffer,
        format="JPEG",
        quality=quality,
    )

    return buffer.getvalue()