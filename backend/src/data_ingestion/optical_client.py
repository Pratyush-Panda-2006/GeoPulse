"""
src/data_ingestion/optical_client.py
====================================
True-color optical basemap fetcher (display-only).

Sentinel-1 is a radar sensor and has no true optical color. When a request
carries a geographic bounding box (the ``/sentinel`` flow), we can fetch a
real true-color satellite basemap for that exact extent and offer it as an
optional "Optical (true color)" layer alongside the colorized SAR.

Provider
--------
Default: Esri **World Imagery** static map export — global coverage, no API
key required, single HTTP GET. The image is requested in EPSG:4326 for the
same bbox and pixel size as the SAR tile, so it aligns with the SAR previews
and the baked change boxes.

    GET .../World_Imagery/MapServer/export
        ?bbox=west,south,east,north&bboxSR=4326&imageSR=4326
        &size=W,H&format=jpg&f=image

Override the endpoint with the ``OPTICAL_BASEMAP_EXPORT_URL`` env var (must be
an ArcGIS-style MapServer ``export`` endpoint). Set ``OPTICAL_BASEMAP_DISABLED``
to any truthy value to disable optical fetching entirely.

Design contract
---------------
This is best-effort and DISPLAY-ONLY. ``fetch_optical_basemap`` never raises:
any failure (no network, provider error, decode failure, disabled) returns
``None`` so the caller simply omits the optical layer. It must never affect
inference or turn a successful detection into a failure.
"""

from __future__ import annotations

import io
import logging
import os
from typing import Any, Optional

import numpy as np
import requests
from PIL import Image

logger = logging.getLogger(__name__)

_DEFAULT_EXPORT_URL = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/export"
)
_REQUEST_TIMEOUT_S = 30
# Provider export limit guard; both Esri and most WMS export services cap here.
_MAX_DIM = 4096


def _is_disabled() -> bool:
    val = os.environ.get("OPTICAL_BASEMAP_DISABLED", "").strip().lower()
    return val not in ("", "0", "false", "no")


def fetch_optical_basemap(
    bbox: list[float],
    size_hw: tuple[int, int],
    target_crs: Any = None,
    target_transform: Any = None,
    timeout: int = _REQUEST_TIMEOUT_S,
) -> Optional[np.ndarray]:
    """
    Fetch a true-color optical basemap for ``bbox`` aligned to a specific raster grid.

    Parameters
    ----------
    bbox : list[float]
        Area of interest as ``[west, south, east, north]`` in EPSG:4326.
    size_hw : tuple[int, int]
        Target ``(height, width)`` in pixels.
    target_crs : rasterio.crs.CRS, optional
        Target coordinate reference system of the SAR array.
    target_transform : affine.Affine, optional
        Target affine transform of the SAR array.
    timeout : int
        Per-request timeout in seconds.

    Returns
    -------
    Optional[np.ndarray]
        ``(H, W, 3)`` uint8 RGB image, or ``None`` if the basemap could not
        be fetched or accurately reprojected (never raises).
    """
    if _is_disabled():
        logger.info("Optical basemap disabled via OPTICAL_BASEMAP_DISABLED.")
        return None

    if not bbox or len(bbox) != 4:
        return None

    height, width = int(size_hw[0]), int(size_hw[1])
    if height <= 0 or width <= 0:
        return None
    # Clamp to the provider's export ceiling, preserving aspect ratio.
    if max(height, width) > _MAX_DIM:
        scale = _MAX_DIM / float(max(height, width))
        width = max(1, int(round(width * scale)))
        height = max(1, int(round(height * scale)))

    west, south, east, north = bbox
    export_url = os.environ.get("OPTICAL_BASEMAP_EXPORT_URL", _DEFAULT_EXPORT_URL)
    params = {
        "bbox": f"{west},{south},{east},{north}",
        "bboxSR": "4326",
        "imageSR": "4326",
        "size": f"{width},{height}",
        "format": "jpg",
        "f": "image",
    }

    try:
        resp = requests.get(export_url, params=params, timeout=timeout)
        if resp.status_code != 200:
            logger.warning(
                "Optical basemap fetch failed: HTTP %s (%s)",
                resp.status_code, resp.text[:200],
            )
            return None
        ctype = resp.headers.get("Content-Type", "")
        if "image" not in ctype:
            # ArcGIS returns a JSON error blob (200) when params are rejected.
            logger.warning("Optical basemap: non-image response (%s).", ctype)
            return None

        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        arr = np.asarray(img, dtype=np.uint8)
        if arr.ndim != 3 or arr.shape[2] != 3:
            return None

        # Geographic Alignment / Reprojection (Phase 7 Requirement)
        # If target metadata is available, strictly reproject. 
        if target_crs is not None and target_transform is not None:
            try:
                from rasterio.warp import reproject, Resampling
                from rasterio.crs import CRS
                from rasterio.transform import from_bounds
                
                src_crs = CRS.from_epsg(4326)
                # Ensure correct bounds order: west, south, east, north
                src_transform = from_bounds(west, south, east, north, arr.shape[1], arr.shape[0])
                
                dst_arr = np.zeros((3, int(size_hw[0]), int(size_hw[1])), dtype=np.uint8)
                src_arr = arr.transpose(2, 0, 1)  # C, H, W
                
                reproject(
                    source=src_arr,
                    destination=dst_arr,
                    src_transform=src_transform,
                    src_crs=src_crs,
                    dst_transform=target_transform,
                    dst_crs=target_crs,
                    resampling=Resampling.bilinear
                )
                
                arr = dst_arr.transpose(1, 2, 0)  # H, W, C
            except Exception as exc:
                logger.warning("Optical alignment/reprojection failed: %s", exc)
                return None  # No naive resize fallback permitted for geographic alignment.
        else:
            # If no target transform is supplied (e.g., non-georeferenced mock data), return None 
            # or skip? The user asked to avoid PIL resize as geographic alignment mechanism.
            # We can return None if they strictly want geographic alignment.
            logger.warning("Optical alignment skipped: Missing target CRS/transform.")
            return None

        logger.info(
            "Optical basemap aligned: bbox=%s size=%dx%d", bbox, arr.shape[1], arr.shape[0]
        )
        return arr
    except Exception as exc:  # noqa: BLE001 — display-only, must never propagate
        logger.warning("Optical basemap fetch error (non-fatal): %s", exc)
        return None
