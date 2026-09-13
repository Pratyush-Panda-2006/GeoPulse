from __future__ import annotations

import hashlib
import sys
import tempfile
from pathlib import Path

import numpy as np
import rasterio
from dotenv import load_dotenv


# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

REPO_ROOT = Path(r"D:\Projects\border surv")
RETRIEVAL_ROOT = Path(r"D:\GeoPulse-Retrieval")
BACKEND_DIR = REPO_ROOT / "backend"

CHECKPOINT = (
    RETRIEVAL_ROOT
    / "models"
    / "RemoteCLIP-RN50.pt"
)

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ------------------------------------------------------------
# Environment
# ------------------------------------------------------------

load_dotenv(
    BACKEND_DIR / ".env",
    override=True,
)


# ------------------------------------------------------------
# GeoPulse imports
# ------------------------------------------------------------

import src.api.db as db_module

from src.api.models import SARSceneAsset

from src.api.services.archive_tiler import (
    generate_tiles,
)

from src.api.services.archive_retrieval_encoder import (
    ArchiveRetrievalEncoder,
)

from src.storage.object_storage import (
    download_bytes,
)


# ------------------------------------------------------------
# SAR -> RGB
# ------------------------------------------------------------

VV_MIN_DB = -22.98
VV_MAX_DB = 5.63

VH_MIN_DB = -32.33
VH_MAX_DB = -2.53


def sar_to_rgb(
    arr: np.ndarray,
):

    arr = arr[:2].astype(
        np.float32
    )

    valid = (
        np.all(
            np.isfinite(arr),
            axis=0,
        )
        & np.all(
            arr > 0.0,
            axis=0,
        )
    )

    safe = np.where(
        np.isfinite(arr) & (arr > 0.0),
        np.maximum(arr, 1e-10),
        1e-10,
    )

    arr_db = (
        10.0
        * np.log10(safe)
    )

    vv = np.clip(
        arr_db[0],
        VV_MIN_DB,
        VV_MAX_DB,
    )

    vh = np.clip(
        arr_db[1],
        VH_MIN_DB,
        VH_MAX_DB,
    )

    vv = (
        vv - VV_MIN_DB
    ) / (
        VV_MAX_DB - VV_MIN_DB
    )

    vh = (
        vh - VH_MIN_DB
    ) / (
        VH_MAX_DB - VH_MIN_DB
    )

    ratio = vv / (
        vh + 1e-6
    )

    valid_ratio = ratio[valid]

    if valid_ratio.size > 0:

        low, high = np.percentile(
            valid_ratio,
            [2, 98],
        )

        ratio = np.clip(
            (
                ratio - low
            )
            / (
                high - low + 1e-8
            ),
            0.0,
            1.0,
        )

    rgb = np.stack(
        [
            vv,
            vh,
            ratio,
        ],
        axis=-1,
    )

    rgb[~valid] = 0.0

    return (
        __import__("PIL")
        .Image
        .fromarray(
            (
                rgb * 255.0
            )
            .clip(
                0,
                255,
            )
            .astype(
                np.uint8
            ),
            mode="RGB",
        )
    )


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():

    print(
        "=== ARCHIVE RETRIEVAL ENCODER TEST ==="
    )

    # --------------------------------------------------------
    # Database
    # --------------------------------------------------------

    db_module.init_db()

    if db_module.SessionLocal is None:
        raise RuntimeError(
            "Database is not initialized."
        )

    db = db_module.SessionLocal()

    try:

        # ----------------------------------------------------
        # Real archive asset #1
        # ----------------------------------------------------

        asset = (
            db.query(
                SARSceneAsset
            )
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
        print(
            "Asset ID:",
            asset.id,
        )

        print(
            "Scene ID:",
            asset.scene_id,
        )

        print(
            "Storage key:",
            asset.storage_key,
        )

        # ----------------------------------------------------
        # Download TIFF
        # ----------------------------------------------------

        print()
        print(
            "Downloading archived TIFF..."
        )

        tiff_bytes = download_bytes(
            asset.storage_key
        )

        checksum = hashlib.sha256(
            tiff_bytes
        ).hexdigest()

        print(
            "Downloaded bytes:",
            len(tiff_bytes),
        )

        print(
            "Checksum match:",
            checksum
            == asset.checksum_sha256,
        )

        if (
            asset.checksum_sha256
            and checksum
            != asset.checksum_sha256
        ):
            raise RuntimeError(
                "Checksum mismatch."
            )

        # ----------------------------------------------------
        # Temporary raster
        # ----------------------------------------------------

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

            # ------------------------------------------------
            # Read raster
            # ------------------------------------------------

            with rasterio.open(
                temp_path
            ) as src:

                arr = src.read().astype(
                    np.float32
                )

                print()
                print(
                    "Raster:",
                    src.width,
                    "x",
                    src.height,
                )

                print(
                    "Bands:",
                    src.count,
                )

            # ------------------------------------------------
            # SAR representation
            # ------------------------------------------------

            print()
            print(
                "Building SAR RGB..."
            )

            rgb = sar_to_rgb(
                arr
            )

            print(
                "RGB:",
                rgb.size,
                rgb.mode,
            )

            # ------------------------------------------------
            # Production tiler
            # ------------------------------------------------

            print()
            print(
                "Generating tiles..."
            )

            tiles = generate_tiles(
                rgb,
                tile_size=224,
                stride=168,
            )

            print(
                "Tile count:",
                len(tiles),
            )

            for tile in tiles:

                print(
                    f"  {tile.tile_id}: "
                    f"x={tile.x}, "
                    f"y={tile.y}"
                )

            # ------------------------------------------------
            # Production encoder
            # ------------------------------------------------

            print()
            print(
                "Creating archive retrieval encoder..."
            )

            encoder = ArchiveRetrievalEncoder(
                CHECKPOINT
            )

            # ------------------------------------------------
            # Batch encode
            # ------------------------------------------------

            print()
            print(
                "Encoding all archive tiles..."
            )

            embeddings = encoder.encode_tiles(
                tiles,
                batch_size=8,
            )

            # ------------------------------------------------
            # Validate output
            # ------------------------------------------------

            print()
            print(
                "=== RESULT ==="
            )

            print(
                "Embedding matrix shape:",
                embeddings.shape,
            )

            print(
                "Embedding dtype:",
                embeddings.dtype,
            )

            print(
                "Expected shape:",
                (
                    len(tiles),
                    1024,
                ),
            )

            if embeddings.shape != (
                len(tiles),
                1024,
            ):
                raise RuntimeError(
                    "Unexpected embedding shape."
                )

            norms = np.linalg.norm(
                embeddings,
                axis=1,
            )

            print()
            print(
                "Embedding norms:"
            )

            for index, norm in enumerate(
                norms
            ):

                print(
                    f"  Tile {index}: "
                    f"{norm:.9f}"
                )

            if not np.allclose(
                norms,
                1.0,
                atol=1e-5,
            ):
                raise RuntimeError(
                    "Embeddings are not normalized."
                )

            # ------------------------------------------------
            # Check pairwise similarity matrix
            # ------------------------------------------------

            similarity = (
                embeddings
                @ embeddings.T
            )

            print()
            print(
                "Similarity matrix shape:",
                similarity.shape,
            )

            print()
            print(
                "Center tile similarities:"
            )

            center_index = next(
                index
                for index, tile in enumerate(
                    tiles
                )
                if tile.tile_id
                == "x168_y168"
            )

            for index, tile in enumerate(
                tiles
            ):

                if index == center_index:
                    continue

                print(
                    f"  center <-> "
                    f"{tile.tile_id}: "
                    f"{similarity[center_index, index]:.6f}"
                )

            # ------------------------------------------------
            # Save embeddings
            # ------------------------------------------------

            output_file = (
                RETRIEVAL_ROOT
                / "experiments"
                / "archive_asset1_9tile_embeddings.npy"
            )

            np.save(
                output_file,
                embeddings,
            )

            print()
            print(
                "Embeddings saved:",
                output_file,
            )

            print()
            print(
                "ARCHIVE RETRIEVAL ENCODER TEST SUCCESSFUL"
            )

        finally:

            temp_path.unlink(
                missing_ok=True
            )

    finally:

        db.close()


if __name__ == "__main__":
    main()