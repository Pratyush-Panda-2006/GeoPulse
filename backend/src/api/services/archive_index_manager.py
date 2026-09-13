from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import faiss
import numpy as np


class ArchiveIndexManager:
    """
    Incremental FAISS index manager for GeoPulse archive retrieval.

    The FAISS index and metadata JSON always share the same ordering:

        vector index 0 -> metadata[0]
        vector index 1 -> metadata[1]
        ...

    This class keeps that invariant intact while allowing new
    archive vectors to be appended without rebuilding the index.
    """

    DIMENSION = 1024

    def __init__(
        self,
        index_path: str | Path,
        metadata_path: str | Path,
    ) -> None:

        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)

        self.index_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.metadata: list[dict] = []

        if self.index_path.exists():
            self.index = faiss.read_index(
                str(self.index_path)
            )

            if self.index.d != self.DIMENSION:
                raise RuntimeError(
                    f"FAISS dimension mismatch: "
                    f"{self.index.d} != {self.DIMENSION}"
                )

        else:
            self.index = faiss.IndexFlatIP(
                self.DIMENSION
            )

        if self.metadata_path.exists():

            with open(
                self.metadata_path,
                "r",
                encoding="utf-8",
            ) as f:
                self.metadata = json.load(f)

            if not isinstance(
                self.metadata,
                list,
            ):
                raise RuntimeError(
                    "Retrieval metadata must be a JSON list."
                )

        self.verify()

    @property
    def count(self) -> int:
        return self.index.ntotal

    def verify(self) -> None:
        """
        Verify the fundamental FAISS/metadata invariant.
        """

        if self.index.d != self.DIMENSION:
            raise RuntimeError(
                f"FAISS dimension must be "
                f"{self.DIMENSION}, got {self.index.d}"
            )

        if self.index.ntotal != len(
            self.metadata
        ):
            raise RuntimeError(
                "FAISS/metadata mismatch: "
                f"{self.index.ntotal} vectors vs "
                f"{len(self.metadata)} metadata records"
            )

    def add(
        self,
        embeddings: np.ndarray,
        metadata_records: list[dict],
    ) -> list[int]:
        """
        Append embeddings and metadata.

        Returns the FAISS indices assigned to the new records.
        """

        embeddings = np.asarray(
            embeddings,
            dtype=np.float32,
        )

        if embeddings.ndim != 2:
            raise ValueError(
                f"Embeddings must be 2-D, got "
                f"{embeddings.shape}"
            )

        if embeddings.shape[1] != self.DIMENSION:
            raise ValueError(
                f"Expected embedding dimension "
                f"{self.DIMENSION}, got "
                f"{embeddings.shape[1]}"
            )

        if len(embeddings) != len(
            metadata_records
        ):
            raise ValueError(
                "Embedding count and metadata count "
                "must match."
            )

        if len(embeddings) == 0:
            return []

        # Defensive normalization.
        faiss.normalize_L2(
            embeddings
        )

        start_index = self.index.ntotal

        self.index.add(
            embeddings
        )

        assigned_indices = list(
            range(
                start_index,
                start_index + len(embeddings),
            )
        )

        for faiss_index, record in zip(
            assigned_indices,
            metadata_records,
        ):

            record = dict(record)

            record["faiss_index"] = (
                faiss_index
            )

            self.metadata.append(
                record
            )

        self.verify()

        return assigned_indices

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
    ) -> list[dict]:
        """
        Search the current index.

        Because the index contains normalized vectors,
        inner product is cosine similarity.
        """

        if top_k < 1:
            raise ValueError(
                "top_k must be >= 1."
            )

        if self.index.ntotal == 0:
            return []

        top_k = min(
            top_k,
            self.index.ntotal,
        )

        query = np.asarray(
            query_embedding,
            dtype=np.float32,
        )

        if query.ndim == 1:
            query = query.reshape(
                1,
                -1,
            )

        if query.shape != (
            1,
            self.DIMENSION,
        ):
            raise ValueError(
                f"Expected query shape "
                f"(1, {self.DIMENSION}), "
                f"got {query.shape}"
            )

        faiss.normalize_L2(
            query
        )

        scores, indices = (
            self.index.search(
                query,
                top_k,
            )
        )

        results = []

        for rank, (
            score,
            index,
        ) in enumerate(
            zip(
                scores[0],
                indices[0],
            ),
            start=1,
        ):

            index = int(index)

            if index < 0:
                continue

            results.append(
                {
                    "rank": rank,
                    "score": float(score),
                    "faiss_index": index,
                    "record": dict(
                        self.metadata[index]
                    ),
                }
            )

        return results

    def save(self) -> None:
        """
        Persist FAISS index and metadata.

        Temporary files are written first so an interrupted
        save is less likely to leave a partially-written file.
        """

        self.verify()

        self.index_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ----------------------------------------------------
        # Save FAISS to temporary file
        # ----------------------------------------------------

        index_fd, index_tmp = (
            tempfile.mkstemp(
                suffix=".index.tmp",
                dir=str(
                    self.index_path.parent
                ),
            )
        )

        os.close(index_fd)

        metadata_fd, metadata_tmp = (
            tempfile.mkstemp(
                suffix=".json.tmp",
                dir=str(
                    self.metadata_path.parent
                ),
            )
        )

        os.close(metadata_fd)

        try:

            faiss.write_index(
                self.index,
                index_tmp,
            )

            with open(
                metadata_tmp,
                "w",
                encoding="utf-8",
            ) as f:

                json.dump(
                    self.metadata,
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            os.replace(
                index_tmp,
                self.index_path,
            )

            os.replace(
                metadata_tmp,
                self.metadata_path,
            )

        finally:

            Path(
                index_tmp
            ).unlink(
                missing_ok=True
            )

            Path(
                metadata_tmp
            ).unlink(
                missing_ok=True
            )

    def get_record(
        self,
        faiss_index: int,
    ) -> dict | None:
        """
        Return metadata for a FAISS index position.
        """

        if faiss_index < 0:
            return None

        if faiss_index >= len(
            self.metadata
        ):
            return None

        return dict(
            self.metadata[
                faiss_index
            ]
        )


__all__ = [
    "ArchiveIndexManager",
]