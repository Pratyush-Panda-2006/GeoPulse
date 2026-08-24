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
from typing import Optional

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
    timeout: int = _REQUEST_TIMEOUT_S,
) -> Optional[np.ndarray]:
    """
    Fetch a true-color optical basemap for ``bbox`` sized to ``size_hw``.

    Parameters
    ----------
    bbox : list[float]
        Area of interest as ``[west, south, east, north]`` in EPSG:4326 —
        the same convention used by :func:`fetch_sentinel1_pair`.
    size_hw : tuple[int, int]
        Target ``(height, width)`` in pixels. Should match the SAR array so
        the optical layer aligns with the SAR previews / change boxes.
    timeout : int
        Per-request timeout in seconds.

    Returns
    -------
    Optional[np.ndarray]
        ``(H, W, 3)`` uint8 RGB image, or ``None`` if the basemap could not
        be fetched for any reason (never raises).
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

        # Resize to the exact requested grid if the provider snapped dimensions.
        if arr.shape[0] != int(size_hw[0]) or arr.shape[1] != int(size_hw[1]):
            img2 = img.resize((int(size_hw[1]), int(size_hw[0])), Image.Resampling.BILINEAR)
            arr = np.asarray(img2, dtype=np.uint8)

        logger.info(
            "Optical basemap fetched: bbox=%s size=%dx%d", bbox, arr.shape[1], arr.shape[0]
        )
        return arr
    except Exception as exc:  # noqa: BLE001 — display-only, must never propagate
        logger.warning("Optical basemap fetch error (non-fatal): %s", exc)
        return None
