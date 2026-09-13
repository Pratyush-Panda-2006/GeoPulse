from __future__ import annotations

import hashlib
import sys
import tempfile
from pathlib import Path

import rasterio
from dotenv import load_dotenv

REPO_ROOT = Path(r"D:\Projects\border surv")
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(
    BACKEND_DIR / ".env",
    override=True,
)

import src.api.db as db_module

from src.api.models import SARSceneAsset
from src.storage.object_storage import download_bytes
from src.api.services.archive_tiler import generate_tiles
from src.api.services.archive_tile_geo import tile_bounds


def main() -> None:

    print("=== ARCHIVE TILE GEOGRAPHY TEST ===")

    db_module.init_db()

    if db_module.SessionLocal is None:
        raise RuntimeError(
            "Database is not initialized."
        )

    db = db_module.SessionLocal()

    try:

        asset = (
            db.query(SARSceneAsset)
            .filter(
                SARSceneAsset.id == 1
            )
            .first()
        )

        if asset is None:
            raise RuntimeError(
                "SARSceneAsset #1 not found."
            )

        print()
        print("Asset ID:", asset.id)
        print("Scene ID:", asset.scene_id)
        print("Storage key:", asset.storage_key)

        print()
        print("Downloading archived TIFF...")

        tiff_bytes = download_bytes(
            asset.storage_key
        )

        checksum = hashlib.sha256(
            tiff_bytes
        ).hexdigest()

        print(
            "Checksum match:",
            checksum == asset.checksum_sha256,
        )

        if (
            asset.checksum_sha256
            and checksum != asset.checksum_sha256
        ):
            raise RuntimeError(
                "Checksum mismatch."
            )

        with tempfile.NamedTemporaryFile(
            suffix=".tif",
            delete=False,
        ) as temp_file:

            temp_path = Path(
                temp_file.name
            )

            temp_file.write(
                tiff_bytes
            )

        try:

            with rasterio.open(
                temp_path
            ) as src:

                print()
                print("Raster:")
                print(
                    "  Size:",
                    src.width,
                    "x",
                    src.height,
                )
                print(
                    "  CRS:",
                    src.crs,
                )
                print(
                    "  Bounds:",
                    src.bounds,
                )
                print(
                    "  Transform:",
                    src.transform,
                )

                # We only need the image dimensions
                # for this test. Use a blank RGB image
                # with the same raster dimensions.
                from PIL import Image

                image = Image.new(
                    "RGB",
                    (
                        src.width,
                        src.height,
                    ),
                )

                tiles = generate_tiles(
                    image,
                    tile_size=224,
                    stride=168,
                )

                print()
                print(
                    "Generated tiles:",
                    len(tiles),
                )

                print()
                print(
                    "Tile geographic footprints:"
                )

                for index, tile in enumerate(
                    tiles
                ):

                    bounds = tile_bounds(
                        transform=src.transform,
                        source_crs=src.crs,
                        x=tile.x,
                        y=tile.y,
                        width=tile.width,
                        height=tile.height,
                    )

                    print()
                    print(
                        f"{index}: {tile.tile_id}"
                    )

                    print(
                        f"  Pixel: "
                        f"x={tile.x}, "
                        f"y={tile.y}, "
                        f"size={tile.width}x{tile.height}"
                    )

                    print(
                        f"  Geographic: "
                        f"west={bounds.west:.8f}, "
                        f"south={bounds.south:.8f}, "
                        f"east={bounds.east:.8f}, "
                        f"north={bounds.north:.8f}"
                    )

                    print(
                        f"  CRS: {bounds.crs}"
                    )

                    if not (
                        bounds.west
                        < bounds.east
                    ):
                        raise RuntimeError(
                            f"Invalid longitude bounds "
                            f"for {tile.tile_id}"
                        )

                    if not (
                        bounds.south
                        < bounds.north
                    ):
                        raise RuntimeError(
                            f"Invalid latitude bounds "
                            f"for {tile.tile_id}"
                        )

                # ------------------------------------------------
                # Verify center tile
                # ------------------------------------------------

                center = next(
                    tile
                    for tile in tiles
                    if tile.tile_id
                    == "x168_y168"
                )

                center_bounds = tile_bounds(
                    transform=src.transform,
                    source_crs=src.crs,
                    x=center.x,
                    y=center.y,
                    width=center.width,
                    height=center.height,
                )

                print()
                print(
                    "Center tile verification:"
                )

                print(
                    "  Tile:",
                    center.tile_id,
                )

                print(
                    "  West:",
                    center_bounds.west,
                )

                print(
                    "  South:",
                    center_bounds.south,
                )

                print(
                    "  East:",
                    center_bounds.east,
                )

                print(
                    "  North:",
                    center_bounds.north,
                )

                # The AOI itself is approximately:
                # 72.8 to 72.9 longitude
                # 18.9 to 19.0 latitude.
                #
                # Therefore every tile must remain
                # inside those broad raster bounds.

                raster_bounds = src.bounds

                if src.crs.to_string() == "EPSG:4326":

                    for tile in tiles:

                        bounds = tile_bounds(
                            transform=src.transform,
                            source_crs=src.crs,
                            x=tile.x,
                            y=tile.y,
                            width=tile.width,
                            height=tile.height,
                        )

                        if (
                            bounds.west
                            < raster_bounds.left
                            - 1e-8
                            or bounds.east
                            > raster_bounds.right
                            + 1e-8
                            or bounds.south
                            < raster_bounds.bottom
                            - 1e-8
                            or bounds.north
                            > raster_bounds.top
                            + 1e-8
                        ):
                            raise RuntimeError(
                                f"Tile {tile.tile_id} "
                                "falls outside raster bounds."
                            )

                print()
                print(
                    "All tile geographic bounds are valid."
                )

                print()
                print(
                    "ARCHIVE TILE GEOGRAPHY TEST SUCCESSFUL"
                )

        finally:

            temp_path.unlink(
                missing_ok=True
            )

    finally:

        db.close()


if __name__ == "__main__":
    main()