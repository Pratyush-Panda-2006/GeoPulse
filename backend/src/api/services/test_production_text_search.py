from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(r"D:\Projects\border surv")
RETRIEVAL_ROOT = Path(r"D:\GeoPulse-Retrieval")
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from src.api.services.archive_retrieval_encoder import (
    ArchiveRetrievalEncoder,
)
from src.api.services.production_archive_retrieval_service import (
    ProductionArchiveRetrievalService,
)


CHECKPOINT = (
    RETRIEVAL_ROOT
    / "models"
    / "RemoteCLIP-RN50.pt"
)

INDEX_PATH = (
    RETRIEVAL_ROOT
    / "experiments"
    / "production_archive_retrieval"
    / "geopulse_archive.index"
)

METADATA_PATH = (
    RETRIEVAL_ROOT
    / "experiments"
    / "production_archive_retrieval"
    / "geopulse_archive_metadata.json"
)


def main() -> None:
    print("=== PRODUCTION TEXT SEARCH TEST ===")

    print("\nLoading RemoteCLIP...")
    encoder = ArchiveRetrievalEncoder(CHECKPOINT)

    print("\nLoading production archive...")
    service = ProductionArchiveRetrievalService(
        encoder=encoder,
        index_path=INDEX_PATH,
        metadata_path=METADATA_PATH,
    )

    print("FAISS vectors:", service.count)

    queries = [
        "large structures",
        "urban area",
        "agricultural fields",
        "water near land",
    ]

    for query in queries:
        print("\n" + "=" * 50)
        print("QUERY:", query)
        print("=" * 50)

        results = service.search_text(
            query,
            top_k=5,
        )

        for result in results:
            record = result["record"]

            print(
                f"\nRank {result['rank']}"
            )
            print(
                "  Similarity:",
                f"{result['score']:.6f}",
            )
            print(
                "  Tile:",
                record.get("tile_id"),
            )
            print(
                "  Asset:",
                record.get("scene_asset_id"),
            )
            print(
                "  Scene:",
                record.get("scene_id"),
            )
            print(
                "  Bounds:",
                record.get("bounds"),
            )

    print("\n" + "=" * 50)
    print("PRODUCTION TEXT SEARCH TEST SUCCESSFUL")
    print("=" * 50)


if __name__ == "__main__":
    main()