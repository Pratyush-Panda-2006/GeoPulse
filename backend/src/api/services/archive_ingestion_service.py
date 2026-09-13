from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from sqlalchemy.orm import Session

from src.api.models import SARSceneAsset
from src.api.services.archive_index_manager import (
    ArchiveIndexManager,
)
from src.api.services.archive_retrieval_encoder import (
    ArchiveRetrievalEncoder,
)
from src.api.services.archive_tile_geo import (
    tile_bounds,
)
from src.api.services.archive_tiler import (
    generate_tiles,
)
from src.storage.object_storage import (
    download_bytes,
)


VV_MIN_DB = -22.98
VV_MAX_DB = 5.63

VH_MIN_DB = -32.33
VH_MAX_DB = -2.53


class ArchiveIngestionService:
    """
    Ingest a stored Sentinel-1 archive asset into the
    production RemoteCLIP retrieval index.

    Pipeline:

        SARSceneAsset
            ↓
        Neon Object Storage
            ↓
        Sentinel-1 VV/VH TIFF
            ↓
        SAR RGB
            ↓
        spatial tiles
            ↓
        geographic bounds
            ↓
        RemoteCLIP embeddings
            ↓
        FAISS + metadata
    """

    PROCESSING_VERSION = (
        "sar-rgb-v1-224px-stride168"
    )

    def __init__(
        self,
        db: Session,
        encoder: ArchiveRetrievalEncoder,
        index_manager: ArchiveIndexManager,
    ) -> None:

        self.db = db
        self.encoder = encoder
        self.index_manager = index_manager

    def ingest_asset(
        self,
        asset_id: int,
    ) -> dict:
        """
        Ingest one SARSceneAsset.

        The operation is idempotent: if this asset has already
        been indexed, no duplicate vectors are added.
        """

        asset = (
            self.db.query(
                SARSceneAsset
            )
            .filter(
                SARSceneAsset.id == asset_id
            )
            .first()
        )

        if asset is None:
            raise ValueError(
                f"SARSceneAsset {asset_id} not found."
            )

        # ----------------------------------------------------
        # Idempotency check
        # ----------------------------------------------------

        existing_indices = [
            record.get("faiss_index")
            for record in self.index_manager.metadata
            if record.get("scene_asset_id")
            == asset.id
        ]

        if existing_indices:

            return {
                "asset_id": asset.id,
                "status": "already_indexed",
                "vectors_added": 0,
                "existing_vectors": len(
                    existing_indices
                ),
                "faiss_indices": existing_indices,
            }

        # ----------------------------------------------------
        # Download archive TIFF
        # ----------------------------------------------------

        tiff_bytes = download_bytes(
            asset.storage_key
        )

        if not tiff_bytes:
            raise RuntimeError(
                f"Empty object returned for "
                f"{asset.storage_key}"
            )

        checksum = hashlib.sha256(
            tiff_bytes
        ).hexdigest()

        if (
            asset.checksum_sha256
            and checksum
            != asset.checksum_sha256
        ):
            raise RuntimeError(
                f"Checksum mismatch for "
                f"asset {asset.id}."
            )

        # ----------------------------------------------------
        # Temporary TIFF
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

                if src.count < 2:
                    raise RuntimeError(
                        f"Asset {asset.id} must contain "
                        "at least VV and VH bands."
                    )

                raster = src.read(
                    [1, 2]
                ).astype(
                    np.float32
                )

                transform = src.transform
                source_crs = src.crs

                raster_width = src.width
                raster_height = src.height

            # ------------------------------------------------
            # SAR → RGB
            # ------------------------------------------------

            rgb = self._sar_to_rgb(
                raster
            )

            # ------------------------------------------------
            # Spatial tiling
            # ------------------------------------------------

            tiles = generate_tiles(
                rgb,
                tile_size=224,
                stride=168,
            )

            if not tiles:
                raise RuntimeError(
                    f"No tiles generated for "
                    f"asset {asset.id}."
                )

            # ------------------------------------------------
            # RemoteCLIP embeddings
            # ------------------------------------------------

            embeddings = (
                self.encoder.encode_tiles(
                    tiles,
                    batch_size=8,
                )
            )

            if len(embeddings) != len(
                tiles
            ):
                raise RuntimeError(
                    "Tile/embedding count mismatch."
                )

            # ------------------------------------------------
            # Build metadata
            # ------------------------------------------------

            metadata_records = []

            for tile in tiles:

                geo = tile_bounds(
                    transform=transform,
                    source_crs=source_crs,
                    x=tile.x,
                    y=tile.y,
                    width=tile.width,
                    height=tile.height,
                )

                tile_id = (
                    f"asset{asset.id}_"
                    f"x{tile.x}_y{tile.y}"
                )

                metadata_records.append(
                    {
                        "tile_id": tile_id,
                        "scene_asset_id": asset.id,
                        "scene_id": asset.scene_id,
                        "storage_key": asset.storage_key,
                        "source_type": "sentinel-1",
                        "sensor": "Sentinel-1",
                        "model_name": (
                            self.encoder.MODEL_NAME
                        ),
                        "model_version": (
                            self.encoder.MODEL_VERSION
                        ),
                        "embedding_dimension": (
                            self.encoder.EMBEDDING_DIMENSION
                        ),
                        "processing_version": (
                            self.PROCESSING_VERSION
                        ),
                        "source_raster_width": (
                            raster_width
                        ),
                        "source_raster_height": (
                            raster_height
                        ),
                        "x": tile.x,
                        "y": tile.y,
                        "width": tile.width,
                        "height": tile.height,
                        "valid_percent": 100.0,
                        "crs": geo.crs,
                        "bounds": {
                            "left": geo.west,
                            "bottom": geo.south,
                            "right": geo.east,
                            "top": geo.north,
                        },
                        "resolution_m": None,
                    }
                )

            # ------------------------------------------------
            # Add to FAISS
            # ------------------------------------------------

            assigned_indices = (
                self.index_manager.add(
                    embeddings,
                    metadata_records,
                )
            )

            # ------------------------------------------------
            # Persist index + metadata
            # ------------------------------------------------

            self.index_manager.save()

            return {
                "asset_id": asset.id,
                "scene_id": asset.scene_id,
                "status": "indexed",
                "vectors_added": len(
                    assigned_indices
                ),
                "faiss_indices": assigned_indices,
                "tile_count": len(tiles),
                "index_total": (
                    self.index_manager.count
                ),
            }

        finally:

            temp_path.unlink(
                missing_ok=True
            )

    @staticmethod
    def _sar_to_rgb(
        arr: np.ndarray,
    ) -> Image.Image:
        """
        Convert Sentinel-1 VV/VH power values into
        the validated 3-channel SAR RGB representation.
        """

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
            np.isfinite(arr)
            & (arr > 0.0),
            np.maximum(
                arr,
                1e-10,
            ),
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

        return Image.fromarray(
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


__all__ = [
    "ArchiveIngestionService",
]