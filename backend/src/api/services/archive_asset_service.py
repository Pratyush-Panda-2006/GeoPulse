from __future__ import annotations

import tempfile
from pathlib import Path

from sqlalchemy.orm import Session

from src.api.models import SARScene, SARSceneAsset
from src.data_ingestion.sentinel_client import SentinelHubClient
from src.storage.object_storage import upload_bytes
from src.storage.tiff_metadata import read_tiff_metadata


def get_existing_asset(
    db: Session,
    scene_id: int,
    bbox: list[float],
) -> SARSceneAsset | None:
    """
    Find an already-downloaded AOI asset for a Sentinel scene.
    """

    return (
        db.query(SARSceneAsset)
        .filter(
            SARSceneAsset.scene_id == scene_id,
            SARSceneAsset.bbox_min_lon == bbox[0],
            SARSceneAsset.bbox_min_lat == bbox[1],
            SARSceneAsset.bbox_max_lon == bbox[2],
            SARSceneAsset.bbox_max_lat == bbox[3],
        )
        .first()
    )


def fetch_scene_asset(
    db: Session,
    sentinel_client: SentinelHubClient,
    scene: SARScene,
    bbox: list[float],
    output_resolution: tuple[int, int] = (512, 512),
) -> SARSceneAsset:
    """
    Fetch and persist an AOI-specific Sentinel-1 asset for a known scene.

    If the same scene/AOI has already been downloaded, the existing asset
    is returned without making another Sentinel request.
    """

    if len(bbox) != 4:
        raise ValueError(
            "bbox must contain [west, south, east, north]"
        )

    west, south, east, north = bbox

    if not west < east or not south < north:
        raise ValueError("Invalid bbox")

    existing = get_existing_asset(
        db=db,
        scene_id=scene.id,
        bbox=bbox,
    )

    if existing:
        return existing

    exact_datetime = scene.acquisition_date.isoformat()

    tiff_bytes = sentinel_client.fetch_tile(
        bbox=bbox,
        exact_datetime=exact_datetime,
        output_resolution=output_resolution,
    )

    if not tiff_bytes:
        raise RuntimeError("Sentinel returned empty GeoTIFF content.")

    with tempfile.NamedTemporaryFile(
        suffix=".tif",
        delete=False,
    ) as temp_file:
        temp_path = Path(temp_file.name)
        temp_file.write(tiff_bytes)

    try:
        metadata = read_tiff_metadata(temp_path)

        storage_key = (
            f"sar/scenes/{scene.id}/"
            f"{west}_{south}_{east}_{north}.tif"
        )

        storage_result = upload_bytes(
            content=tiff_bytes,
            object_key=storage_key,
            content_type="image/tiff",
        )

        asset = SARSceneAsset(
            scene_id=scene.id,
            bbox_min_lon=west,
            bbox_min_lat=south,
            bbox_max_lon=east,
            bbox_max_lat=north,
            storage_key=storage_result["storage_key"],
            mime_type="image/tiff",
            file_size_bytes=storage_result["file_size_bytes"],
            checksum_sha256=storage_result["checksum_sha256"],
            width=metadata["width"],
            height=metadata["height"],
            band_count=metadata["band_count"],
            bands=metadata["bands"],
            crs=metadata["crs"],
            has_georeference=metadata["crs"] is not None,
        )

        db.add(asset)
        db.commit()
        db.refresh(asset)

        return asset

    finally:
        temp_path.unlink(missing_ok=True)
