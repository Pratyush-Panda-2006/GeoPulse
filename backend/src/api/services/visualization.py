"""
src/api/services/visualization.py
==================================
Visualization helpers for SAR dual-polarization imagery, change masks,
and confidence heatmaps, with Base64 encoding for REST API responses.
"""

from __future__ import annotations

import base64
import io
from typing import Optional
import numpy as np
import scipy.ndimage as ndimage
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import matplotlib.cm as cm


def array_to_base64_png(img_array: np.ndarray) -> str:
    """
    Convert a uint8 NumPy array (H, W), (H, W, 3), or (H, W, 4) to a base64 PNG string.
    """
    if img_array.dtype != np.uint8:
        img_array = np.clip(img_array * 255.0, 0, 255).astype(np.uint8)

    img = Image.fromarray(img_array)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def array_to_base64_jpeg(img_array: np.ndarray, quality: int = 90) -> str:
    """
    Convert a uint8 NumPy array (H, W) or (H, W, 3) to a base64 JPEG string for smaller payload sizes.
    """
    if img_array.dtype != np.uint8:
        img_array = np.clip(img_array * 255.0, 0, 255).astype(np.uint8)

    img = Image.fromarray(img_array)
    if img.mode == "RGBA":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"


def sar_dualpol_to_rgb(sar_array: np.ndarray) -> np.ndarray:
    """
    Convert a 2-band normalized SAR array (2, H, W) in [0, 1] into a high-contrast false-color RGB image (H, W, 3) uint8.
    Applies percentile clipping to maintain contrast despite outlier scatterers.

    Channels:
      - Red:   VV backscatter
      - Green: VH backscatter
      - Blue:  VV / (VH + 1e-3) ratio scaled
    """
    if sar_array.ndim != 3 or sar_array.shape[0] != 2:
        raise ValueError(f"Expected shape (2, H, W), got {sar_array.shape}")

    vv = np.nan_to_num(sar_array[0], nan=0.0, posinf=1.0, neginf=0.0)
    vh = np.nan_to_num(sar_array[1], nan=0.0, posinf=1.0, neginf=0.0)

    # Compute ratio channel for blue
    ratio = np.clip(vv / (vh + 0.1), 0.0, 3.0) / 3.0

    def robust_scale(band: np.ndarray, pmin: float = 2.0, pmax: float = 98.0) -> np.ndarray:
        vmin, vmax = np.percentile(band, (pmin, pmax))
        if vmax > vmin:
            scaled = (band - vmin) / (vmax - vmin)
        else:
            scaled = band
        return np.clip(scaled * 255.0, 0, 255).astype(np.uint8)

    r = robust_scale(vv)
    g = robust_scale(vh)
    b = robust_scale(ratio)

    rgb = np.stack([r, g, b], axis=-1)
    return rgb


# ============================================================================
# Clean grayscale SAR rendering (display-only)
# ----------------------------------------------------------------------------
# NOTE: These helpers are for HUMAN-READABLE display ONLY. They never touch the
# arrays that feed Model 3 inference (inference runs upstream and operates on
# the untouched normalized tensors). The input arrays are already in the
# dB-normalized domain: sar_loader maps 10*log10(power) linearly to [0, 1] via
# locked per-band dB bounds (VV_MIN_DB..VH_MAX_DB), so stretching here is
# effectively stretching in dB space. We therefore do NOT re-apply log scaling.
# ============================================================================

def _lee_filter(img: np.ndarray, size: int = 5) -> np.ndarray:
    """
    Conservative, edge-preserving Lee speckle filter for SAR intensity.

    Output = local_mean + k * (pixel - local_mean), where
        k = local_var / (local_var + overall_var).
    In homogeneous regions (low local variance) k -> 0, so output approaches the
    local mean and multiplicative speckle is suppressed. Near edges/structures
    (high local variance) k -> 1, so the original value is preserved. This keeps
    the filter conservative: it never blurs strong scatterers or boundaries.
    """
    img = img.astype(np.float32, copy=False)
    mean = ndimage.uniform_filter(img, size=size)
    mean_sq = ndimage.uniform_filter(img * img, size=size)
    local_var = np.clip(mean_sq - mean * mean, 0.0, None)
    overall_var = float(np.var(img))
    k = local_var / (local_var + overall_var + 1e-8)
    out = mean + k * (img - mean)
    return out.astype(np.float32)


def _clahe(
    img01: np.ndarray,
    tiles: int = 8,
    clip_limit: float = 2.5,
    n_bins: int = 256,
) -> np.ndarray:
    """
    Contrast Limited Adaptive Histogram Equalization for a float image in [0, 1].

    Pure-NumPy implementation (cv2/skimage are not installed). The image is split
    into a ``tiles`` x ``tiles`` grid; each tile gets a clipped-histogram CDF
    mapping (mass above ``clip_limit`` * mean-bin-height is clipped and
    redistributed uniformly). Per-pixel mappings are bilinearly interpolated
    between the four surrounding tile mappings to avoid visible block seams.

    Parameters
    ----------
    clip_limit:
        Clip threshold expressed as a multiple of the mean histogram height.
        Higher -> stronger local contrast (closer to plain AHE); lower -> milder.
    """
    img = np.clip(np.nan_to_num(img01, nan=0.0), 0.0, 1.0).astype(np.float32)
    h, w = img.shape
    ty = max(1, int(tiles))
    tx = max(1, int(tiles))

    ys = np.linspace(0, h, ty + 1).astype(int)
    xs = np.linspace(0, w, tx + 1).astype(int)

    # Quantize to histogram bins.
    q = np.clip((img * (n_bins - 1)).astype(np.int32), 0, n_bins - 1)

    # Build one bin->intensity LUT per tile.
    maps = np.empty((ty, tx, n_bins), dtype=np.float32)
    identity = np.linspace(0.0, 1.0, n_bins, dtype=np.float32)
    for iy in range(ty):
        for ix in range(tx):
            tile = q[ys[iy]:ys[iy + 1], xs[ix]:xs[ix + 1]].ravel()
            n = tile.size
            if n == 0:
                maps[iy, ix] = identity
                continue
            hist = np.bincount(tile, minlength=n_bins).astype(np.float32)
            # Clip tall bins and redistribute the excess uniformly.
            limit = max(1.0, clip_limit * (n / n_bins))
            clipped = np.minimum(hist, limit)
            excess = float((hist - clipped).sum())
            clipped += excess / n_bins
            cdf = np.cumsum(clipped)
            cdf_min = float(cdf[0])
            denom = float(cdf[-1]) - cdf_min
            if denom <= 0.0:
                maps[iy, ix] = identity
            else:
                maps[iy, ix] = ((cdf - cdf_min) / denom).astype(np.float32)

    # Per-pixel bilinear interpolation of tile mappings.
    # Fractional tile-center coordinates, clamped so borders use the nearest tile.
    row = np.arange(h)
    col = np.arange(w)
    fy = np.clip((row + 0.5) * ty / h - 0.5, 0.0, ty - 1)
    fx = np.clip((col + 0.5) * tx / w - 0.5, 0.0, tx - 1)

    iy0 = np.floor(fy).astype(int)
    ix0 = np.floor(fx).astype(int)
    iy1 = np.minimum(iy0 + 1, ty - 1)
    ix1 = np.minimum(ix0 + 1, tx - 1)
    wy = (fy - iy0).astype(np.float32)[:, None]   # (H, 1)
    wx = (fx - ix0).astype(np.float32)[None, :]   # (1, W)

    iy0 = iy0[:, None]; iy1 = iy1[:, None]         # (H, 1)
    ix0 = ix0[None, :]; ix1 = ix1[None, :]         # (1, W)

    m00 = maps[iy0, ix0, q]
    m01 = maps[iy0, ix1, q]
    m10 = maps[iy1, ix0, q]
    m11 = maps[iy1, ix1, q]

    top = m00 + wx * (m01 - m00)
    bot = m10 + wx * (m11 - m10)
    out = top + wy * (bot - top)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def _unsharp_mask(img: np.ndarray, sigma: float = 1.0, amount: float = 0.6) -> np.ndarray:
    """
    Mild unsharp-mask sharpening for a float image in [0, 1]. Boosts edge/detail
    crispness so the preview holds up better when zoomed in the viewer.
    """
    blur = ndimage.gaussian_filter(img, sigma=sigma)
    sharp = img + amount * (img - blur)
    return np.clip(sharp, 0.0, 1.0).astype(np.float32)


def _sar_enhanced_gray01(
    sar_array: np.ndarray,
    lee_size: int = 5,
    clahe_tiles: int = 8,
    clahe_clip: float = 2.5,
    pmin: float = 2.0,
    pmax: float = 98.0,
    sharpen: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Shared display-enhancement pipeline for the VV co-pol band. Returns
    ``(enhanced01, valid)`` where ``enhanced01`` is a float32 image in [0, 1] and
    ``valid`` is the boolean non-nodata mask. Both grayscale and colorized
    renderers build on this so they stay visually consistent.

    Pipeline: NaN/Inf cleanup -> Lee speckle filter -> robust p2/p98 stretch over
    valid pixels -> CLAHE -> optional unsharp mask. Fully out-of-place; the input
    (which also feeds inference) is never modified.
    """
    if sar_array.ndim != 3 or sar_array.shape[0] != 2:
        raise ValueError(f"Expected shape (2, H, W), got {sar_array.shape}")

    vv = np.nan_to_num(
        sar_array[0].astype(np.float32), nan=0.0, posinf=1.0, neginf=0.0
    )
    vv = np.clip(vv, 0.0, 1.0)

    valid = vv > 0.0  # nodata pixels are normalized to exactly 0 by sar_loader

    denoised = _lee_filter(vv, size=lee_size)

    sample = denoised[valid] if np.any(valid) else denoised
    lo, hi = np.percentile(sample, (pmin, pmax))
    if hi > lo:
        stretched = np.clip((denoised - lo) / (hi - lo), 0.0, 1.0)
    else:
        stretched = np.clip(denoised, 0.0, 1.0)

    enhanced = _clahe(stretched, tiles=clahe_tiles, clip_limit=clahe_clip)
    if sharpen:
        enhanced = _unsharp_mask(enhanced)

    return enhanced.astype(np.float32), valid


def sar_to_grayscale(
    sar_array: np.ndarray,
    lee_size: int = 5,
    clahe_tiles: int = 8,
    clahe_clip: float = 2.5,
    pmin: float = 2.0,
    pmax: float = 98.0,
) -> np.ndarray:
    """
    Render a clean, human-readable grayscale SAR image from a normalized
    dual-pol array (2, H, W) in [0, 1]. Returns (H, W, 3) uint8 (gray replicated
    across channels so the result feeds both JPEG previews and the RGB overlay).

    Display-only; operates fully out-of-place (see :func:`_sar_enhanced_gray01`).
    """
    enhanced, valid = _sar_enhanced_gray01(
        sar_array, lee_size=lee_size, clahe_tiles=clahe_tiles,
        clahe_clip=clahe_clip, pmin=pmin, pmax=pmax,
    )
    enhanced = enhanced.copy()
    enhanced[~valid] = 0.0  # keep no-data black
    gray8 = np.clip(enhanced * 255.0, 0, 255).astype(np.uint8)
    return np.stack([gray8, gray8, gray8], axis=-1)


# ---------------------------------------------------------------------------
# Colorized ("satellite-style") SAR rendering (display-only)
# ---------------------------------------------------------------------------
# HONEST NOTE: Sentinel-1 is a radar sensor; it has no true optical color. This
# is a perceptual LUT applied to the enhanced VV intensity (dark smooth surfaces
# -> deep teal/blue, mid -> greens/olive, bright rough/urban -> tan/white), with
# a subtle green lift where the VH cross-pol (volume scattering, e.g. vegetation)
# is strong. It reads far more naturally than stark grayscale, but it is
# colorized radar, NOT a photographic satellite image. Inference is untouched.

def _build_ramp_lut(anchors: list[tuple[float, tuple[int, int, int]]], n: int = 256) -> np.ndarray:
    """Interpolate (position, RGB) anchors into an (n, 3) uint8 lookup table."""
    xs = np.array([a[0] for a in anchors], dtype=np.float32)
    cols = np.array([a[1] for a in anchors], dtype=np.float32)  # (k, 3)
    grid = np.linspace(0.0, 1.0, n, dtype=np.float32)
    lut = np.empty((n, 3), dtype=np.float32)
    for c in range(3):
        lut[:, c] = np.interp(grid, xs, cols[:, c])
    return np.clip(lut, 0, 255).astype(np.uint8)


def sar_to_colorized(
    sar_array: np.ndarray,
    lee_size: int = 5,
    clahe_tiles: int = 8,
    clahe_clip: float = 2.5,
    pmin: float = 2.0,
    pmax: float = 98.0,
    veg_boost: float = 0.5,
) -> np.ndarray:
    """
    Render a colorized "satellite-style" SAR image from a normalized dual-pol
    array (2, H, W) in [0, 1]. Returns (H, W, 3) uint8.

    The VV intensity drives an adaptive earth-tone LUT derived from the scene's
    own cross-pol statistics. The VH cross-pol adds a subtle green lift for
    vegetation-like volume scattering. Display-only and fully out-of-place — see
    the module note above on why this is colorized radar, not true optical color.
    """
    enhanced, valid = _sar_enhanced_gray01(
        sar_array, lee_size=lee_size, clahe_tiles=clahe_tiles,
        clahe_clip=clahe_clip, pmin=pmin, pmax=pmax,
    )

    vv_raw = np.clip(np.nan_to_num(sar_array[0].astype(np.float32), nan=0.0), 0.0, 1.0)
    vh_raw = np.clip(np.nan_to_num(sar_array[1].astype(np.float32), nan=0.0), 0.0, 1.0)

    # Build scene-adaptive palette
    if np.any(valid):
        vv_valid = vv_raw[valid]
        vh_valid = vh_raw[valid]
        
        vv_med = float(np.median(vv_valid))
        vh_med = float(np.median(vh_valid))
        
        # Cross-pol ratio indicates volume scattering (vegetation)
        cross_ratio = vh_med / (vv_med + 1e-5)
        
        # ~0.15 is bare/water/urban, ~0.6+ is dense vegetation
        veg_weight = np.clip((cross_ratio - 0.15) / 0.45, 0.0, 1.0)
        
        c0 = (1.0 - veg_weight) * np.array([15, 25, 35]) + veg_weight * np.array([10, 30, 20])
        c1 = (1.0 - veg_weight) * np.array([55, 50, 45]) + veg_weight * np.array([35, 60, 45])
        c2 = (1.0 - veg_weight) * np.array([150, 130, 100]) + veg_weight * np.array([80, 140, 70])
        c3 = (1.0 - veg_weight) * np.array([210, 190, 150]) + veg_weight * np.array([160, 190, 110])
        c4 = np.array([250, 245, 240])

        anchors = [
            (0.00, tuple(c0.astype(int))),
            (0.20, tuple(c1.astype(int))),
            (0.50, tuple(c2.astype(int))),
            (0.80, tuple(c3.astype(int))),
            (1.00, tuple(c4.astype(int))),
        ]
        scene_lut = _build_ramp_lut(anchors, n=256)
    else:
        # Fallback to grayscale if completely empty/invalid
        scene_lut = np.stack([np.arange(256)]*3, axis=-1).astype(np.uint8)

    idx = np.clip((enhanced * 255.0).astype(np.int32), 0, 255)
    rgb = scene_lut[idx].astype(np.float32)  # (H, W, 3)

    # Subtle vegetation-like green lift from strong VH cross-pol backscatter.
    if veg_boost > 0.0 and np.any(valid):
        vh = vh_raw
        vlo, vhi = np.percentile(vh[valid], (5.0, 95.0))
        vh_n = np.clip((vh - vlo) / (vhi - vlo), 0.0, 1.0) if vhi > vlo else vh
        # Only lift mid-tones (avoid tinting water/shadow or blown-out urban).
        mid = enhanced * (1.0 - enhanced) * 4.0  # peaks at 0.5, 0 at extremes
        lift = (veg_boost * 26.0) * vh_n * mid
        rgb[..., 1] = np.clip(rgb[..., 1] + lift, 0, 255)

    rgb[~valid] = 0.0  # keep no-data black
    return rgb.astype(np.uint8)


def generate_change_mask_image(binary_mask: np.ndarray) -> np.ndarray:
    """
    Convert binary mask (H, W) {0, 1} or bool into a high-contrast RGB image (H, W, 3).
    Change pixels are rendered in bright cyan-white or red.
    """
    h, w = binary_mask.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    # Bright coral red for changes
    rgb[binary_mask > 0] = [255, 69, 58]
    return rgb


def generate_heatmap_image(prob_map: np.ndarray, colormap_name: str = "turbo") -> np.ndarray:
    """
    Render probability map [0.0, 1.0] (H, W) as an RGBA/RGB colormap heatmap.
    """
    prob_clean = np.clip(np.nan_to_num(prob_map, nan=0.0), 0.0, 1.0)
    cmap = plt.get_cmap(colormap_name)
    colored = cmap(prob_clean) # (H, W, 4) in [0, 1]
    rgb = (colored[:, :, :3] * 255).astype(np.uint8)
    return rgb


def generate_overlay_image(base_rgb: np.ndarray, binary_mask: np.ndarray, alpha: float = 0.65) -> np.ndarray:
    """
    Create a blended overlay of the change mask on top of the base SAR false-color image.
    Uses a strong bright color and high alpha for high visibility in human analysis.
    """
    overlay = base_rgb.copy().astype(np.float32)
    mask_indices = binary_mask > 0

    # Highlight change in bright yellow/cyan [255, 235, 59] for strong contrast against dark SAR
    highlight_color = np.array([255, 235, 59], dtype=np.float32)
    overlay[mask_indices] = (1.0 - alpha) * overlay[mask_indices] + alpha * highlight_color
    return np.clip(overlay, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Change-region bounding boxes (display-only annotation)
# ---------------------------------------------------------------------------
# Per-severity outline colors (RGB). Match the frontend severity palette so the
# baked-in boxes stay consistent with the Analytics/legend colors.
SEVERITY_COLORS = {
    "Critical": (255, 64, 64),
    "High": (255, 148, 0),
    "Medium": (255, 214, 0),
    "Low": (80, 220, 120),
    "Uncertain": (0, 208, 255),
}
_DEFAULT_BOX_COLOR = (255, 64, 64)


def _region_field(region, name, default=None):
    """Read a field from a ChangedRegion (attribute) or a plain dict."""
    if isinstance(region, dict):
        return region.get(name, default)
    return getattr(region, name, default)


def _load_label_font(size: int):
    """Best-effort scalable font; fall back to PIL's bitmap default."""
    for candidate in ("arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def draw_change_boxes(
    base_rgb: np.ndarray,
    regions,
    thickness: int = 3,
    padding: int = 4,
    draw_labels: bool = True,
    max_boxes: Optional[int] = None,
) -> np.ndarray:
    """
    Draw labeled, severity-colored bounding boxes over a base RGB image to
    highlight the detected change clusters (the "one button" highlight view).

    Parameters
    ----------
    base_rgb:
        (H, W, 3) uint8 image to annotate (typically the colorized T2 SAR).
    regions:
        Iterable of ChangedRegion objects (or dicts) with ``bbox_xy``
        (min_row, min_col, max_row, max_col), ``severity`` and ``region_id``.
    thickness, padding:
        Outline width and how many pixels to inflate each box for legibility.
    draw_labels:
        Draw an "A{region_id}" chip at each box's top-left corner.
    max_boxes:
        If set, only annotate the first N regions (regions are already sorted
        by area descending, so this keeps the largest/most significant ones).

    Display-only; the input array is not modified (drawing happens on a copy).
    """
    if base_rgb.dtype != np.uint8:
        base_rgb = np.clip(base_rgb, 0, 255).astype(np.uint8)

    img = Image.fromarray(base_rgb.copy(), mode="RGB")
    draw = ImageDraw.Draw(img)
    h, w = base_rgb.shape[:2]

    font_size = max(13, int(round(min(h, w) / 42.0)))
    font = _load_label_font(font_size) if draw_labels else None

    items = list(regions or [])
    if max_boxes is not None:
        items = items[:max_boxes]

    for region in items:
        bbox = _region_field(region, "bbox_xy")
        if not bbox or len(bbox) != 4:
            continue
        min_row, min_col, max_row, max_col = (int(v) for v in bbox)

        severity = _region_field(region, "severity", "Medium")
        color = SEVERITY_COLORS.get(severity, _DEFAULT_BOX_COLOR)

        x0 = max(0, min_col - padding)
        y0 = max(0, min_row - padding)
        x1 = min(w - 1, max_col + padding)
        y1 = min(h - 1, max_row + padding)
        if x1 <= x0 or y1 <= y0:
            continue

        draw.rectangle([x0, y0, x1, y1], outline=color, width=thickness)

        if draw_labels and font is not None:
            rid = _region_field(region, "region_id", "")
            text = f"A{rid}"
            try:
                tb = draw.textbbox((0, 0), text, font=font)
                tw, th = tb[2] - tb[0], tb[3] - tb[1]
            except Exception:
                tw, th = 8 * len(text), font_size
            pad = 3
            # Prefer a chip just above the box; drop inside if there's no room.
            chip_y1 = y0
            chip_y0 = y0 - (th + 2 * pad)
            if chip_y0 < 0:
                chip_y0 = y0
                chip_y1 = y0 + (th + 2 * pad)
            chip_x0 = x0
            chip_x1 = min(w - 1, x0 + tw + 2 * pad)
            draw.rectangle([chip_x0, chip_y0, chip_x1, chip_y1], fill=color)
            # Dark text on bright chips, white on dark chips (luminance test).
            lum = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
            text_fill = (20, 20, 20) if lum > 140 else (255, 255, 255)
            draw.text((chip_x0 + pad, chip_y0 + pad), text, fill=text_fill, font=font)

    return np.asarray(img, dtype=np.uint8)
