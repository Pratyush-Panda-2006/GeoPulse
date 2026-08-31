import hashlib
from pathlib import Path

import rasterio


def calculate_sha256(path: str | Path) -> str:
    path = Path(path)

    sha256 = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def read_tiff_metadata(path: str | Path) -> dict:
    path = Path(path)

    with rasterio.open(path) as src:
        return {
            "width": src.width,
            "height": src.height,
            "band_count": src.count,
            "bands": ",".join(src.dtypes),
            "crs": str(src.crs) if src.crs else None,
            "file_size_bytes": path.stat().st_size,
            "checksum_sha256": calculate_sha256(path),
        }