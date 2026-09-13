from __future__ import annotations

import os
import sys
from pathlib import Path

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

OUTPUT_DIR = (
    RETRIEVAL_ROOT
    / "experiments"
    / "production_archive_retrieval"
)

INDEX_PATH = (
    OUTPUT_DIR
    / "geopulse_archive.index"
)

METADATA_PATH = (
    OUTPUT_DIR
    / "geopulse_archive_metadata.json"
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

from src.api.services.archive_index_manager import (
    ArchiveIndexManager,
)

from src.api.services.archive_ingestion_service import (
    ArchiveIngestionService,
)

from src.api.services.archive_retrieval_encoder import (
    ArchiveRetrievalEncoder,
)


def main() -> None:

    print(
        "=== PRODUCTION ARCHIVE INGESTION TEST ==="
    )

    # --------------------------------------------------------
    # Output directory
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
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
        # Encoder
        # ----------------------------------------------------

        print()
        print(
            "Loading RemoteCLIP encoder..."
        )

        encoder = ArchiveRetrievalEncoder(
            CHECKPOINT
        )

        # ----------------------------------------------------
        # Index manager
        # ----------------------------------------------------

        print()
        print(
            "Creating archive FAISS index..."
        )

        index_manager = ArchiveIndexManager(
            index_path=INDEX_PATH,
            metadata_path=METADATA_PATH,
        )

        print(
            "Initial vectors:",
            index_manager.count,
        )

        # ----------------------------------------------------
        # Ingestion service
        # ----------------------------------------------------

        ingestion = ArchiveIngestionService(
            db=db,
            encoder=encoder,
            index_manager=index_manager,
        )

        # ----------------------------------------------------
        # Asset 1
        # ----------------------------------------------------

        print()
        print(
            "----------------------------------------"
        )

        print(
            "INGESTING ASSET 1"
        )

        result_1 = ingestion.ingest_asset(
            asset_id=1
        )

        print()
        print(
            "Asset 1 result:"
        )

        for key, value in result_1.items():

            print(
                f"  {key}: {value}"
            )

        # ----------------------------------------------------
        # Asset 2
        # ----------------------------------------------------

        print()
        print(
            "----------------------------------------"
        )

        print(
            "INGESTING ASSET 2"
        )

        result_2 = ingestion.ingest_asset(
            asset_id=2
        )

        print()
        print(
            "Asset 2 result:"
        )

        for key, value in result_2.items():

            print(
                f"  {key}: {value}"
            )

        # ----------------------------------------------------
        # Final verification
        # ----------------------------------------------------

        print()
        print(
            "========================================"
        )

        print(
            "FINAL INDEX"
        )

        print(
            "FAISS vectors:",
            index_manager.count,
        )

        print(
            "Metadata records:",
            len(
                index_manager.metadata
            ),
        )

        index_manager.verify()

        if index_manager.count != 18:
            raise RuntimeError(
                f"Expected 18 vectors, "
                f"got {index_manager.count}"
            )

        if len(
            index_manager.metadata
        ) != 18:
            raise RuntimeError(
                "Expected 18 metadata records."
            )

        # ----------------------------------------------------
        # Distribution by asset
        # ----------------------------------------------------

        asset_1_records = [
            record
            for record
            in index_manager.metadata
            if record.get(
                "scene_asset_id"
            ) == 1
        ]

        asset_2_records = [
            record
            for record
            in index_manager.metadata
            if record.get(
                "scene_asset_id"
            ) == 2
        ]

        print()
        print(
            "Asset 1 indexed tiles:",
            len(asset_1_records),
        )

        print(
            "Asset 2 indexed tiles:",
            len(asset_2_records),
        )

        if len(
            asset_1_records
        ) != 9:
            raise RuntimeError(
                "Asset 1 should have 9 tiles."
            )

        if len(
            asset_2_records
        ) != 9:
            raise RuntimeError(
                "Asset 2 should have 9 tiles."
            )

        # ----------------------------------------------------
        # FAISS index positions
        # ----------------------------------------------------

        print()
        print(
            "FAISS index positions:"
        )

        for record in (
            index_manager.metadata
        ):

            print(
                f"  "
                f"{record['faiss_index']:2d} "
                f"asset={record['scene_asset_id']} "
                f"scene={record['scene_id']} "
                f"tile={record['tile_id']}"
            )

        # ----------------------------------------------------
        # Save/reload verification
        # ----------------------------------------------------

        print()
        print(
            "Reloading production index..."
        )

        reloaded = ArchiveIndexManager(
            index_path=INDEX_PATH,
            metadata_path=METADATA_PATH,
        )

        print(
            "Reloaded vectors:",
            reloaded.count,
        )

        print(
            "Reloaded metadata:",
            len(
                reloaded.metadata
            ),
        )

        reloaded.verify()

        if reloaded.count != 18:
            raise RuntimeError(
                "Reloaded FAISS count incorrect."
            )

        # ----------------------------------------------------
        # Check idempotency
        # ----------------------------------------------------

        print()
        print(
            "Testing idempotency with Asset 1..."
        )

        before_count = (
            index_manager.count
        )

        duplicate_result = (
            ingestion.ingest_asset(
                asset_id=1
            )
        )

        after_count = (
            index_manager.count
        )

        print(
            "Duplicate ingestion result:"
        )

        for key, value in (
            duplicate_result.items()
        ):

            print(
                f"  {key}: {value}"
            )

        print(
            "Vectors before:",
            before_count,
        )

        print(
            "Vectors after:",
            after_count,
        )

        if before_count != after_count:
            raise RuntimeError(
                "Idempotency failed: "
                "duplicate vectors were added."
            )

        if duplicate_result.get(
            "status"
        ) != "already_indexed":

            raise RuntimeError(
                "Expected already_indexed status."
            )

        print()
        print(
            "Production index:"
        )

        print(
            "  FAISS:",
            INDEX_PATH,
        )

        print(
            "  Metadata:",
            METADATA_PATH,
        )

        print()
        print(
            "PRODUCTION ARCHIVE INGESTION "
            "TEST SUCCESSFUL"
        )

    finally:

        db.close()


if __name__ == "__main__":
    main()