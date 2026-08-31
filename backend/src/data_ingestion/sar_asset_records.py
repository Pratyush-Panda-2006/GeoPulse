from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from src.api.models import SARAsset
from src.storage.tiff_metadata import read_tiff_metadata


def create_asset_record(
    db: Session,
    request_id: int,
    time_label: str,
    storage_key: str,
    local_tiff_path: str | Path,
    scene_id: int | None = None,
    asset_key: str | None = None,
) -> SARAsset:
    metadata = read_tiff_metadata(local_tiff_path)

    asset = SARAsset(
        request_id=request_id,
        time_label=time_label,
        scene_id=scene_id,
        asset_key=asset_key,
        storage_key=storage_key,
        mime_type="image/tiff",
        file_size_bytes=metadata["file_size_bytes"],
        checksum_sha256=metadata["checksum_sha256"],
        width=metadata["width"],
        height=metadata["height"],
        band_count=metadata["band_count"],
        bands=metadata["bands"],
        crs=metadata["crs"],
    )

    db.add(asset)
    db.commit()
    db.refresh(asset)

    return asset