from __future__ import annotations

from src.storage.object_storage import upload_bytes


def store_sar_pair(
    request_id: int,
    t1_bytes: bytes,
    t2_bytes: bytes,
) -> tuple[dict, dict]:
    """
    Store raw T1 and T2 Sentinel-1 GeoTIFF bytes.

    Returns:
        (t1_metadata, t2_metadata)
    """

    t1_key = f"sar/requests/{request_id}/T1.tif"
    t2_key = f"sar/requests/{request_id}/T2.tif"

    t1_result = upload_bytes(
        content=t1_bytes,
        object_key=t1_key,
        content_type="image/tiff",
    )

    t2_result = upload_bytes(
        content=t2_bytes,
        object_key=t2_key,
        content_type="image/tiff",
    )

    return t1_result, t2_result