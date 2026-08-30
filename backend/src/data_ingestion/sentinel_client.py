"""
src/data_ingestion/sentinel_client.py
======================================
Copernicus Data Space Ecosystem (CDSE) / Sentinel Hub client for
automated Sentinel-1 GRD SAR imagery ingestion.

Public API
----------
    fetch_sentinel1_pair(
        bbox, date_t1_range, date_t2_range,
        output_resolution=(512, 512),
        save_dir=None,
    ) -> tuple[np.ndarray, np.ndarray]

        Returns (t1_array, t2_array) as float32 NumPy arrays
        with shape (C, H, W) where C=2 (VV, VH).

Authentication
--------------
    Uses OAuth2 client_credentials flow against CDSE identity provider.
    Credentials are loaded from environment variables:
        CDSE_CLIENT_ID
        CDSE_CLIENT_SECRET

    The token is cached in-memory and automatically refreshed 60 s
    before expiry — no manual token management required.

Error handling
--------------
    SentinelAPIError            — HTTP-level failures from the API
    SentinelSceneNotFoundError  — No valid scene in the requested AOI/date
    Transient 429 / 5xx errors  — Exponential back-off (max 3 retries)
"""

from __future__ import annotations

import io
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import numpy as np
import requests
from dotenv import load_dotenv

# ── Logging ────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── CDSE endpoint constants ────────────────────────────────────────────────────
_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu"
    "/auth/realms/CDSE/protocol/openid-connect/token"
)
_PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"
_CATALOG_URL = "https://sh.dataspace.copernicus.eu/api/v1/catalog/1.0.0/search"

# Back-off parameters for transient errors
_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0   # seconds; doubles each retry

# Token refresh safety margin
_TOKEN_REFRESH_MARGIN_S = 60


# ── Custom exceptions ──────────────────────────────────────────────────────────

class SentinelAPIError(RuntimeError):
    """Raised for non-recoverable HTTP errors from the CDSE API."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"[HTTP {status_code}] {message}")
        self.status_code = status_code


class SentinelSceneNotFoundError(ValueError):
    """Raised when no valid Sentinel-1 scene exists for the given AOI/date."""


# ── Authentication manager ─────────────────────────────────────────────────────

class CDSEAuthManager:
    """
    OAuth2 client_credentials token manager for CDSE.

    Token lifecycle
    ---------------
    - First call to ``get_token()`` performs a real token request.
    - Subsequent calls return the cached token unless it expires within
      ``_TOKEN_REFRESH_MARGIN_S`` seconds, in which case a fresh token
      is fetched transparently.

    Thread safety
    -------------
    Not thread-safe by design — add a threading.Lock if using in a
    multi-threaded context.

    Parameters
    ----------
    client_id : str, optional
        CDSE OAuth client ID. Defaults to ``CDSE_CLIENT_ID`` env var.
    client_secret : str, optional
        CDSE OAuth client secret. Defaults to ``CDSE_CLIENT_SECRET`` env var.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ) -> None:
        load_dotenv()

        self._client_id = client_id or os.environ.get("CDSE_CLIENT_ID")
        self._client_secret = client_secret or os.environ.get("CDSE_CLIENT_SECRET")

        if not self._client_id or not self._client_secret:
            raise EnvironmentError(
                "CDSE credentials not found. "
                "Set CDSE_CLIENT_ID and CDSE_CLIENT_SECRET in your .env file "
                "or pass them explicitly to CDSEAuthManager()."
            )

        self._access_token: Optional[str] = None
        self._token_expiry: float = 0.0  # Unix timestamp

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_token(self) -> str:
        """
        Return a valid Bearer access token, fetching/refreshing as needed.

        Returns
        -------
        str
            A valid OAuth2 access token string.
        """
        if self._token_is_valid():
            return self._access_token  # type: ignore[return-value]

        self._refresh_token()
        return self._access_token  # type: ignore[return-value]

    @property
    def expires_in(self) -> float:
        """Seconds until the current token expires (may be negative if expired)."""
        return self._token_expiry - time.monotonic()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _token_is_valid(self) -> bool:
        if self._access_token is None:
            return False
        return time.monotonic() < (self._token_expiry - _TOKEN_REFRESH_MARGIN_S)

    def _refresh_token(self) -> None:
        logger.debug("Requesting new CDSE access token …")

        connect_timeout = int(os.environ.get("CDSE_CONNECT_TIMEOUT_SEC", 30))
        read_timeout = int(os.environ.get("CDSE_READ_TIMEOUT_SEC", 30))
        
        response = requests.post(
            _TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
            timeout=(connect_timeout, read_timeout),
        )

        if response.status_code != 200:
            raise SentinelAPIError(
                response.status_code,
                f"Token request failed: {response.text[:500]}",
            )

        payload = response.json()
        self._access_token = payload["access_token"]
        # expires_in is seconds from now; use monotonic for drift-safety
        self._token_expiry = time.monotonic() + float(payload.get("expires_in", 3600))

        logger.info(
            "CDSE token acquired. Expires in ~%.0f s.",
            payload.get("expires_in", 3600),
        )


# ── Evalscript ─────────────────────────────────────────────────────────────────

def _build_evalscript() -> str:
    """
    Build a Sentinel Hub evalscript that returns VV and VH backscatter
    as float32 linear power values.

    Processing configuration:
        - Collection : sentinel-1-grd
        - Acq. mode  : IW
        - Polarization: DV (VV + VH)
        - backCoeff  : SIGMA0_ELLIPSOID
        - orthorectify: true
        - demInstance : COPERNICUS_30
    """
    return """
//VERSION=3

function setup() {
    return {
        input: [{
            bands: ["VV", "VH"],
            units: "LINEAR_POWER"
        }],
        output: {
            bands: 2,
            sampleType: "FLOAT32"
        }
    };
}

function evaluatePixel(sample) {
    // Return VV (channel 0) and VH (channel 1) as linear power.
    // Clamp negatives that may arise from terrain correction artefacts.
    return [
        Math.max(sample.VV, 0.0),
        Math.max(sample.VH, 0.0)
    ];
}
"""


# ── Request body builder ───────────────────────────────────────────────────────

def _build_request_body(
    bbox: list[float],
    time_from: str,
    time_to: str,
    output_resolution: tuple[int, int],
) -> dict:
    """
    Construct the Sentinel Hub Processing API request body.

    Parameters
    ----------
    bbox : list[float]
        [west, south, east, north] in EPSG:4326.
    time_from : str
        Start time in ISO-8601 format ("YYYY-MM-DDTHH:MM:SSZ").
    time_to : str
        End time in ISO-8601 format ("YYYY-MM-DDTHH:MM:SSZ").
    output_resolution : tuple[int, int]
        (width, height) in pixels of the output tile.

    Returns
    -------
    dict
        JSON-serialisable request payload.
    """
    height, width = output_resolution

    return {
        "input": {
            "bounds": {
                "bbox": bbox,
                "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
            },
            "data": [
                {
                    "type": "sentinel-1-grd",
                    "dataFilter": {
                        "timeRange": {
                            "from": time_from,
                            "to": time_to,
                        },
                        "acquisitionMode": "IW",
                        "polarization": "DV",
                        "resolution": "HIGH",
                    },
                    "processing": {
                        "backCoeff": "SIGMA0_ELLIPSOID",
                        "orthorectify": True,
                        "demInstance": "COPERNICUS_30",
                    },
                }
            ],
        },
        "output": {
            "width": width,
            "height": height,
            "responses": [
                {
                    "identifier": "default",
                    "format": {"type": "image/tiff"},
                }
            ],
        },
        "evalscript": _build_evalscript(),
    }


# ── HTTP helper with retry ─────────────────────────────────────────────────────

def _post_with_retry(
    url: str,
    headers: dict,
    body: dict,
    max_retries: int = _MAX_RETRIES,
) -> requests.Response:
    """
    POST ``body`` to ``url`` with exponential back-off on 429 / 5xx.

    Parameters
    ----------
    url : str
    headers : dict
    body : dict
        Will be sent as JSON.
    max_retries : int

    Returns
    -------
    requests.Response
        The successful response object.

    Raises
    ------
    SentinelAPIError
        If all retries are exhausted or a non-retryable error occurs.
    """
    attempt = 0
    last_exc: Optional[SentinelAPIError] = None

    while attempt <= max_retries:
        if attempt > 0:
            wait = _BACKOFF_BASE ** attempt
            logger.warning(
                "Retry %d/%d after %.1f s …", attempt, max_retries, wait
            )
            time.sleep(wait)

        connect_timeout = int(os.environ.get("CDSE_CONNECT_TIMEOUT_SEC", 30))
        read_timeout = int(os.environ.get("CDSE_READ_TIMEOUT_SEC", 120))
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=body,
                timeout=(connect_timeout, read_timeout),
            )
        except requests.exceptions.Timeout as exc:
            last_exc = SentinelAPIError(0, f"Request timed out: {exc}")
            attempt += 1
            continue
        except requests.exceptions.ConnectionError as exc:
            last_exc = SentinelAPIError(0, f"Connection error: {exc}")
            attempt += 1
            continue

        if response.status_code == 200:
            return response

        # Retryable transient errors
        if response.status_code in (429, 500, 502, 503, 504):
            last_exc = SentinelAPIError(
                response.status_code,
                response.text[:500],
            )
            attempt += 1
            continue

        # Non-retryable
        raise SentinelAPIError(response.status_code, response.text[:500])

    assert last_exc is not None
    raise last_exc


# ── Sentinel Hub client ────────────────────────────────────────────────────────

class SentinelHubClient:
    """
    Thin wrapper around the Sentinel Hub Processing API.

    Parameters
    ----------
    auth : CDSEAuthManager
        Authenticated token manager.
    """

    def __init__(self, auth: CDSEAuthManager) -> None:
        self._auth = auth

    def fetch_scene_metadata(
        self,
        bbox: list[float],
        date_range: tuple[str, str],
    ) -> dict:
        """
        Query the STAC Catalog API to find the most recent Sentinel-1 GRD scene
        in the specified date range and bounding box.
        """
        token = self._auth.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        from_date, to_date = date_range
        datetime_str = f"{from_date}T00:00:00Z/{to_date}T23:59:59Z"
        
        body = {
            "collections": ["sentinel-1-grd"],
            "bbox": bbox,
            "datetime": datetime_str,
            "limit": 1
        }
        
        logger.info("Searching Catalog for %s in %s", bbox, datetime_str)
        response = _post_with_retry(_CATALOG_URL, headers, body)
        data = response.json()
        
        features = data.get("features", [])
        if not features:
            raise SentinelSceneNotFoundError(
                f"No valid Sentinel-1 scene found in catalog for bbox={bbox} dates={date_range}."
            )
            
        feature = features[0]
        return {
            "provider": "CDSE",
            "scene_id": feature["id"],
            "acquisition_date": feature["properties"]["datetime"],
            "bbox": feature["bbox"]
        }

    def fetch_tile(
        self,
        bbox: list[float],
        exact_datetime: str,
        output_resolution: tuple[int, int] = (512, 512),
    ) -> bytes:
        """
        Fetch a Sentinel-1 GRD tile as raw GeoTIFF bytes for an exact datetime.

        Parameters
        ----------
        bbox : list[float]
            [west, south, east, north] in EPSG:4326.
        exact_datetime : str
            Exact ISO-8601 timestamp of the scene (e.g. from fetch_scene_metadata).
        output_resolution : tuple[int, int]
            (width, height) in pixels.

        Returns
        -------
        bytes
            Raw GeoTIFF content.

        Raises
        ------
        SentinelSceneNotFoundError
            When the API returns an empty or no-data response.
        SentinelAPIError
            For HTTP-level failures.
        """
        import datetime as dt

        token = self._auth.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "image/tiff",
        }

        # Narrow timeRange to 1 minute around the exact datetime
        acq = dt.datetime.fromisoformat(exact_datetime.replace("Z", "+00:00"))
        t_from = (acq - dt.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        t_to = (acq + dt.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

        body = _build_request_body(bbox, t_from, t_to, output_resolution)

        logger.info(
            "Fetching S1 tile: bbox=%s  timeRange=[%s, %s]  res=%s",
            bbox, t_from, t_to, output_resolution,
        )

        response = _post_with_retry(_PROCESS_URL, headers, body)

        content = response.content
        if len(content) < 128:
            raise SentinelSceneNotFoundError(
                f"No valid Sentinel-1 scene found for bbox={bbox} "
                f"exact_datetime={exact_datetime}."
            )

        logger.info("Tile fetched: %.1f KB", len(content) / 1024)
        return content


# ── Top-level convenience function ─────────────────────────────────────────────

def fetch_sentinel1_pair(
    bbox: list[float],
    date_t1_range: tuple[str, str],
    date_t2_range: tuple[str, str],
    output_resolution: tuple[int, int] = (512, 512),
    save_dir: Optional[str | Path] = None,
    auth: Optional[CDSEAuthManager] = None,
) -> tuple[np.ndarray, np.ndarray, dict, dict]:
    """
    Fetch a Sentinel-1 SAR image pair for change-detection inference.

    Fetches two GRD tiles (T1 and T2) over the same AOI and decodes
    them into normalized float32 NumPy tensors with shape ``(C, H, W)``
    where ``C=2`` (VV=band 0, VH=band 1).

    Parameters
    ----------
    bbox : list[float]
        Area of interest as ``[west, south, east, north]`` in EPSG:4326.
    date_t1_range : tuple[str, str]
        T1 acquisition window ``("YYYY-MM-DD", "YYYY-MM-DD")``.
    date_t2_range : tuple[str, str]
        T2 acquisition window ``("YYYY-MM-DD", "YYYY-MM-DD")``.
    output_resolution : tuple[int, int]
        Output tile size in pixels ``(width, height)``. Default: ``(512, 512)``.
    save_dir : str or Path, optional
        If provided, raw GeoTIFF bytes for T1 and T2 are saved to this
        directory as ``t1.tif`` and ``t2.tif`` before decoding.
    auth : CDSEAuthManager, optional
        Pre-constructed auth manager. If ``None``, a new one is created
        using environment variables ``CDSE_CLIENT_ID`` / ``CDSE_CLIENT_SECRET``.

    Returns
    -------
    tuple[np.ndarray, np.ndarray, dict, dict, float, float, float]
        ``(t1_array, t2_array, t1_meta, t2_meta, metadata_ms, download_ms, preprocessing_ms)``
        with values normalized to ``[0, 1]``, their metadata dicts, and stage timings.

    Raises
    ------
    SentinelSceneNotFoundError
        If either T1 or T2 has no valid scene in the requested window.
    SentinelAPIError
        For unrecoverable HTTP-level API failures.
    EnvironmentError
        If CDSE credentials are not set.
    """
    # Lazy import to avoid circular dependency
    from preprocessing.sar_loader import decode_geotiff_response, normalize_sar_tensor

    if auth is None:
        auth = CDSEAuthManager()

    client = SentinelHubClient(auth)

    # ── Fetch Metadata ────────────────────────────────────────────────────────
    t_start_metadata = time.perf_counter()
    logger.info("Fetching T1 metadata …")
    t1_meta = client.fetch_scene_metadata(bbox, date_t1_range)
    
    logger.info("Fetching T2 metadata …")
    t2_meta = client.fetch_scene_metadata(bbox, date_t2_range)
    metadata_ms = (time.perf_counter() - t_start_metadata) * 1000.0

    # ── Fetch Tiles ───────────────────────────────────────────────────────────
    t_start_download = time.perf_counter()
    logger.info("Fetching T1 tile …")
    t1_bytes = client.fetch_tile(bbox, t1_meta["acquisition_date"], output_resolution)

    logger.info("Fetching T2 tile …")
    t2_bytes = client.fetch_tile(bbox, t2_meta["acquisition_date"], output_resolution)
    download_ms = (time.perf_counter() - t_start_download) * 1000.0

    # ── Optional: persist GeoTIFFs to disk ───────────────────────────────────
    if save_dir is not None:
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        (save_path / "t1.tif").write_bytes(t1_bytes)
        (save_path / "t2.tif").write_bytes(t2_bytes)
        logger.info("GeoTIFFs saved to %s", save_path)

    # ── Decode + normalize ────────────────────────────────────────────────────
    t_start_preprocessing = time.perf_counter()
    t1_raw = decode_geotiff_response(t1_bytes)
    t2_raw = decode_geotiff_response(t2_bytes)

    t1_norm = normalize_sar_tensor(t1_raw, is_linear=False)
    t2_norm = normalize_sar_tensor(t2_raw, is_linear=False)
    preprocessing_ms = (time.perf_counter() - t_start_preprocessing) * 1000.0

    # ── Extract geospatial metadata for alignment ─────────────────────────────
    try:
        from src.preprocessing.sar_loader import extract_geotiff_metadata
        t_start_metadata_ext = time.perf_counter()
        t2_meta["raster_metadata"] = extract_geotiff_metadata(t2_bytes)
        metadata_ms += (time.perf_counter() - t_start_metadata_ext) * 1000.0
    except Exception as exc:
        logger.warning("Could not extract geodata from T2: %s", exc)

    logger.info(
        "Pair ready: T1 %s  T2 %s  dtype=%s  range=[%.3f, %.3f]",
        t1_norm.shape, t2_norm.shape, t1_norm.dtype,
        t1_norm.min(), t1_norm.max(),
    )

    return t1_norm, t2_norm, t1_meta, t2_meta, metadata_ms, download_ms, preprocessing_ms
