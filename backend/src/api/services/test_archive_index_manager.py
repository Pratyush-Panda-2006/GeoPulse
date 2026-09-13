from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from src.api.services.archive_index_manager import (
    ArchiveIndexManager,
)


def main() -> None:

    print("=== ARCHIVE INDEX MANAGER TEST ===")

    with tempfile.TemporaryDirectory() as temp_dir:

        temp_dir = Path(temp_dir)

        index_path = (
            temp_dir / "test.index"
        )

        metadata_path = (
            temp_dir / "test_metadata.json"
        )

        # ----------------------------------------------------
        # Create empty manager
        # ----------------------------------------------------

        manager = ArchiveIndexManager(
            index_path=index_path,
            metadata_path=metadata_path,
        )

        print(
            "Initial vectors:",
            manager.count,
        )

        # ----------------------------------------------------
        # Create deterministic test vectors
        # ----------------------------------------------------

        rng = np.random.default_rng(
            seed=42
        )

        vectors_a = rng.normal(
            size=(3, 1024)
        ).astype(
            np.float32
        )

        metadata_a = [
            {
                "scene_asset_id": 101,
                "tile_id": "asset101_x0_y0",
            },
            {
                "scene_asset_id": 101,
                "tile_id": "asset101_x168_y0",
            },
            {
                "scene_asset_id": 101,
                "tile_id": "asset101_x288_y0",
            },
        ]

        # ----------------------------------------------------
        # First incremental add
        # ----------------------------------------------------

        indices_a = manager.add(
            vectors_a,
            metadata_a,
        )

        print()
        print(
            "First add indices:",
            indices_a,
        )

        print(
            "Vectors after first add:",
            manager.count,
        )

        if indices_a != [
            0,
            1,
            2,
        ]:
            raise RuntimeError(
                "First FAISS indices are incorrect."
            )

        # ----------------------------------------------------
        # Second incremental add
        # ----------------------------------------------------

        vectors_b = rng.normal(
            size=(2, 1024)
        ).astype(
            np.float32
        )

        metadata_b = [
            {
                "scene_asset_id": 102,
                "tile_id": "asset102_x0_y0",
            },
            {
                "scene_asset_id": 102,
                "tile_id": "asset102_x168_y0",
            },
        ]

        indices_b = manager.add(
            vectors_b,
            metadata_b,
        )

        print()
        print(
            "Second add indices:",
            indices_b,
        )

        print(
            "Vectors after second add:",
            manager.count,
        )

        if indices_b != [
            3,
            4,
        ]:
            raise RuntimeError(
                "Incremental FAISS indices are incorrect."
            )

        # ----------------------------------------------------
        # Verify metadata alignment
        # ----------------------------------------------------

        print()
        print(
            "Checking metadata alignment..."
        )

        expected_tile_ids = [
            "asset101_x0_y0",
            "asset101_x168_y0",
            "asset101_x288_y0",
            "asset102_x0_y0",
            "asset102_x168_y0",
        ]

        for index, expected_tile_id in enumerate(
            expected_tile_ids
        ):

            record = manager.get_record(
                index
            )

            if record is None:
                raise RuntimeError(
                    f"Missing metadata at index {index}"
                )

            actual_tile_id = record.get(
                "tile_id"
            )

            print(
                f"  {index}: {actual_tile_id}"
            )

            if actual_tile_id != expected_tile_id:
                raise RuntimeError(
                    f"Metadata mismatch at "
                    f"index {index}"
                )

        # ----------------------------------------------------
        # Verify count invariant
        # ----------------------------------------------------

        manager.verify()

        print()
        print(
            "FAISS vectors:",
            manager.count,
        )

        print(
            "Metadata records:",
            len(manager.metadata),
        )

        if manager.count != 5:
            raise RuntimeError(
                "Expected 5 vectors."
            )

        if len(manager.metadata) != 5:
            raise RuntimeError(
                "Expected 5 metadata records."
            )

        # ----------------------------------------------------
        # Search using vector 0
        # ----------------------------------------------------

        print()
        print(
            "Testing search..."
        )

        results = manager.search(
            vectors_a[0],
            top_k=3,
        )

        for result in results:

            print(
                f"  rank={result['rank']} "
                f"index={result['faiss_index']} "
                f"score={result['score']:.6f} "
                f"tile={result['record']['tile_id']}"
            )

        if not results:
            raise RuntimeError(
                "Search returned no results."
            )

        if results[0]["faiss_index"] != 0:
            raise RuntimeError(
                "Expected vector 0 to retrieve itself."
            )

        if results[0]["score"] < 0.999:
            raise RuntimeError(
                "Self similarity unexpectedly low."
            )

        # ----------------------------------------------------
        # Save
        # ----------------------------------------------------

        print()
        print(
            "Saving index..."
        )

        manager.save()

        if not index_path.exists():
            raise RuntimeError(
                "FAISS index was not saved."
            )

        if not metadata_path.exists():
            raise RuntimeError(
                "Metadata was not saved."
            )

        print(
            "Index saved:",
            index_path,
        )

        print(
            "Metadata saved:",
            metadata_path,
        )

        # ----------------------------------------------------
        # Reload
        # ----------------------------------------------------

        print()
        print(
            "Reloading manager..."
        )

        reloaded = ArchiveIndexManager(
            index_path=index_path,
            metadata_path=metadata_path,
        )

        print(
            "Reloaded vectors:",
            reloaded.count,
        )

        print(
            "Reloaded metadata:",
            len(reloaded.metadata),
        )

        reloaded.verify()

        if reloaded.count != 5:
            raise RuntimeError(
                "Reloaded vector count incorrect."
            )

        # ----------------------------------------------------
        # Search after reload
        # ----------------------------------------------------

        print()
        print(
            "Testing search after reload..."
        )

        reload_results = reloaded.search(
            vectors_a[0],
            top_k=3,
        )

        for result in reload_results:

            print(
                f"  rank={result['rank']} "
                f"index={result['faiss_index']} "
                f"score={result['score']:.6f} "
                f"tile={result['record']['tile_id']}"
            )

        if (
            not reload_results
            or reload_results[0]["faiss_index"] != 0
        ):
            raise RuntimeError(
                "Reloaded index search failed."
            )

        print()
        print(
            "ARCHIVE INDEX MANAGER TEST SUCCESSFUL"
        )


if __name__ == "__main__":
    main()