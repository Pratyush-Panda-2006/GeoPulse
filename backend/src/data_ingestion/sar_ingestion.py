from __future__ import annotations

from src.data_ingestion.sentinel_client import (
    CDSEAuthManager,
    SentinelHubClient,
)


def fetch_sar_pair_raw(
    bbox: list[float],
    date_t1_range: tuple[str, str],
    date_t2_range: tuple[str, str],
    output_resolution: tuple[int, int] = (512, 512),
    auth: CDSEAuthManager | None = None,
) -> tuple[bytes, bytes, dict, dict]:
    """
    Fetch raw Sentinel-1 GeoTIFF bytes for T1 and T2 along with scene metadata.

    Returns:
        (t1_bytes, t2_bytes, t1_meta, t2_meta)
    """
    if auth is None:
        auth = CDSEAuthManager()

    client = SentinelHubClient(auth)

    t1_meta = client.fetch_scene_metadata(bbox, date_t1_range)
    t2_meta = client.fetch_scene_metadata(bbox, date_t2_range)

    t1_bytes = client.fetch_tile(
        bbox=bbox,
        exact_datetime=t1_meta["acquisition_date"],
        output_resolution=output_resolution,
    )

    t2_bytes = client.fetch_tile(
        bbox=bbox,
        exact_datetime=t2_meta["acquisition_date"],
        output_resolution=output_resolution,
    )

    return t1_bytes, t2_bytes, t1_meta, t2_meta