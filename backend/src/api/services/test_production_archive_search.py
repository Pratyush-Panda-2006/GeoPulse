from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from PIL import Image


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

from src.api.services.archive_index_manager import (
    ArchiveIndexManager,
)

from src.api.services.archive_retrieval_encoder import (
    ArchiveRetrievalEncoder,
)


def main() -> None:

    print(
        "=== PRODUCTION ARCHIVE SEARCH TEST ==="
    )

    # --------------------------------------------------------
    # Load production index
    # --------------------------------------------------------

    print()
    print(
        "Loading production FAISS index..."
    )

    manager = ArchiveIndexManager(
        index_path=INDEX_PATH,
        metadata_path=METADATA_PATH,
    )

    print(
        "Vectors:",
        manager.count,
    )

    print(
        "Metadata:",
        len(manager.metadata),
    )

    manager.verify()

    # --------------------------------------------------------
    # Load RemoteCLIP
    # --------------------------------------------------------

    print()
    print(
        "Loading RemoteCLIP..."
    )

    encoder = ArchiveRetrievalEncoder(
        CHECKPOINT
    )

    # --------------------------------------------------------
    # Select a known production tile
    # --------------------------------------------------------

    query_tile_id = (
        "asset1_x168_y168"
    )

    query_record = None

    for record in manager.metadata:

        if record.get(
            "tile_id"
        ) == query_tile_id:

            query_record = record
            break

    if query_record is None:
        raise RuntimeError(
            f"Query tile not found: "
            f"{query_tile_id}"
        )

    print()
    print(
        "Query tile:"
    )

    print(
        "  Tile ID:",
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
        "  FAISS index:",
        query_record["faiss_index"],
    )

    print(
        "  Bounds:",
        query_record["bounds"],
    )

    # --------------------------------------------------------
    # Load query vector directly from FAISS
    #
    # This first test intentionally uses the stored vector.
    # That isolates FAISS search from image preprocessing.
    # --------------------------------------------------------

    query_index = int(
        query_record["faiss_index"]
    )

    query_vector = manager.index.reconstruct(
        query_index
    )

    query_vector = np.asarray(
        query_vector,
        dtype=np.float32,
    )

    print()
    print(
        "Query vector shape:",
        query_vector.shape,
    )

    print(
        "Query vector norm:",
        np.linalg.norm(
            query_vector
        ),
    )

    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

    print()
    print(
        "Searching production archive..."
    )

    results = manager.search(
        query_vector,
        top_k=10,
    )

    # --------------------------------------------------------
    # Display results
    # --------------------------------------------------------

    print()
    print(
        "========================================"
    )

    print(
        "TOP RESULTS"
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
            record.get(
                "tile_id"
            ),
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

    # --------------------------------------------------------
    # Find corresponding tile in Asset 2
    # --------------------------------------------------------

    corresponding_tile_id = (
        "asset2_x168_y168"
    )

    corresponding_result = None

    for result in results:

        if result["record"].get(
            "tile_id"
        ) == corresponding_tile_id:

            corresponding_result = result
            break

    print()
    print(
        "========================================"
    )

    if corresponding_result:

        print(
            "CORRESPONDING HISTORICAL TILE FOUND"
        )

        print(
            "Tile:",
            corresponding_result[
                "record"
            ]["tile_id"],
        )

        print(
            "Similarity:",
            f"{corresponding_result['score']:.6f}",
        )

        print(
            "Rank:",
            corresponding_result["rank"],
        )

    else:

        print(
            "Corresponding Asset 2 tile "
            "was not in top 10."
        )

    # --------------------------------------------------------
    # Same-location retrieval check
    # --------------------------------------------------------

    asset_2_same_position = None

    for record in manager.metadata:

        if record.get(
            "tile_id"
        ) == corresponding_tile_id:

            asset_2_same_position = record
            break

    if asset_2_same_position is None:
        raise RuntimeError(
            "Corresponding Asset 2 tile "
            "does not exist."
        )

    asset_2_index = int(
        asset_2_same_position[
            "faiss_index"
        ]
    )

    asset_2_vector = manager.index.reconstruct(
        asset_2_index
    )

    asset_2_vector = np.asarray(
        asset_2_vector,
        dtype=np.float32,
    )

    cross_date_similarity = float(
        np.dot(
            query_vector,
            asset_2_vector,
        )
    )

    print()
    print(
        "Same spatial tile across dates:"
    )

    print(
        "  Asset 1:",
        query_tile_id,
    )

    print(
        "  Asset 2:",
        corresponding_tile_id,
    )

    print(
        "  Cosine similarity:",
        f"{cross_date_similarity:.6f}",
    )

    # --------------------------------------------------------
    # Basic correctness checks
    # --------------------------------------------------------

    if not results:
        raise RuntimeError(
            "Production search returned no results."
        )

    if results[0]["faiss_index"] != query_index:
        raise RuntimeError(
            "Query tile did not retrieve itself "
            "as the top result."
        )

    if results[0]["score"] < 0.999:
        raise RuntimeError(
            "Self similarity unexpectedly low."
        )

    if not np.isfinite(
        cross_date_similarity
    ):
        raise RuntimeError(
            "Cross-date similarity is not finite."
        )

    print()
    print(
        "========================================"
    )

    print(
        "PRODUCTION ARCHIVE SEARCH TEST SUCCESSFUL"
    )


if __name__ == "__main__":
    main()