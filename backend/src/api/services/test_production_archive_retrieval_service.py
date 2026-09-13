from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

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

QUERY_IMAGE = (
    RETRIEVAL_ROOT
    / "experiments"
    / "sar_tiles"
    / "mumbai"
    / "mumbai_date1_x224_y448.png"
)


def main() -> None:

    print(
        "=== PRODUCTION ARCHIVE RETRIEVAL SERVICE TEST ==="
    )

    # --------------------------------------------------------
    # Load encoder
    # --------------------------------------------------------

    print()
    print("Loading RemoteCLIP...")

    encoder = ArchiveRetrievalEncoder(
        CHECKPOINT
    )

    # --------------------------------------------------------
    # Load production service
    # --------------------------------------------------------

    print()
    print(
        "Loading production archive index..."
    )

    service = (
        ProductionArchiveRetrievalService(
            encoder=encoder,
            index_path=INDEX_PATH,
            metadata_path=METADATA_PATH,
        )
    )

    print(
        "FAISS vectors:",
        service.count,
    )

    if service.count != 18:
        raise RuntimeError(
            f"Expected 18 production vectors, "
            f"got {service.count}"
        )

    # --------------------------------------------------------
    # Find a production tile
    # --------------------------------------------------------

    query_tile_id = (
        "asset1_x168_y168"
    )

    query_record = (
        service.get_record_by_tile_id(
            query_tile_id
        )
    )

    if query_record is None:
        raise RuntimeError(
            f"Production tile not found: "
            f"{query_tile_id}"
        )

    print()
    print("Production metadata lookup:")
    print(
        "  Tile:",
        query_record["tile_id"],
    )
    print(
        "  Asset:",
        query_record["scene_asset_id"],
    )
    print(
        "  Scene:",
        query_record["scene_id"],
    )
    print(
        "  Bounds:",
        query_record["bounds"],
    )

    # --------------------------------------------------------
    # Create a deterministic query image
    #
    # Use the stored production tile itself. This verifies
    # the complete image -> encoder -> FAISS path.
    #
    # We reconstruct it from the archive TIFF indirectly
    # through the already-tested production tile if available.
    # For this service test, use one of the existing SAR tile
    # images if present.
    # --------------------------------------------------------

    fallback_images = [
        RETRIEVAL_ROOT
        / "experiments"
        / "sar_tiles"
        / "abudhabi"
        / "abudhabi_date1_x0_y0.png",
        RETRIEVAL_ROOT
        / "experiments"
        / "sar_tiles"
        / "mumbai"
        / "mumbai_date1_x224_y448.png",
    ]

    image_path = None

    for candidate in fallback_images:

        if candidate.exists():

            image_path = candidate
            break

    if image_path is None:
        raise RuntimeError(
            "No existing SAR retrieval tile "
            "was found for the image-search test."
        )

    print()
    print(
        "Query image:",
        image_path,
    )

    with Image.open(
        image_path
    ) as image:

        print(
            "Query size:",
            image.size,
        )

        results = service.search_image(
            image,
            top_k=10,
        )

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    print()
    print(
        "========================================"
    )
    print(
        "PRODUCTION IMAGE SEARCH RESULTS"
    )
    print(
        "========================================"
    )

    for result in results:

        record = result["record"]

        print()
        print(
            f"Rank {result['rank']}"
        )

        print(
            "  Similarity:",
            f"{result['score']:.6f}",
        )

        print(
            "  FAISS index:",
            result["faiss_index"],
        )

        print(
            "  Tile:",
            record.get("tile_id"),
        )

        print(
            "  Asset:",
            record.get(
                "scene_asset_id"
            ),
        )

        print(
            "  Scene:",
            record.get(
                "scene_id"
            ),
        )

        print(
            "  Bounds:",
            record.get(
                "bounds"
            ),
        )

    if not results:
        raise RuntimeError(
            "Production image search "
            "returned no results."
        )

    # --------------------------------------------------------
    # Metadata lookup test
    # --------------------------------------------------------

    print()
    print(
        "Testing tile metadata lookup..."
    )

    record = (
        service.get_record_by_tile_id(
            results[0]["record"]["tile_id"]
        )
    )

    if record is None:
        raise RuntimeError(
            "Could not retrieve metadata "
            "for top search result."
        )

    print(
        "Top result metadata lookup: OK"
    )

    # --------------------------------------------------------
    # Final validation
    # --------------------------------------------------------

    print()
    print(
        "Production index count:",
        service.count,
    )

    print(
        "Returned results:",
        len(results),
    )

    print()
    print(
        "PRODUCTION ARCHIVE RETRIEVAL "
        "SERVICE TEST SUCCESSFUL"
    )


if __name__ == "__main__":
    main()