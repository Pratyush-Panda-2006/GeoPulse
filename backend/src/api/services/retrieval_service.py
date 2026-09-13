from __future__ import annotations

import json
import os
from pathlib import Path

import faiss
import numpy as np
from PIL import Image

from src.api.services.retrieval_encoder import RetrievalEncoder


class RetrievalService:
    """
    GeoPulse image retrieval service backed by
    RemoteCLIP and FAISS.
    """

    def __init__(
        self,
        encoder: RetrievalEncoder,
        index_path: str | Path,
        metadata_path: str | Path,
    ) -> None:
        self.encoder = encoder
        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)

        if not self.index_path.exists():
            raise FileNotFoundError(
                f"FAISS index not found: {self.index_path}"
            )

        if not self.metadata_path.exists():
            raise FileNotFoundError(
                f"Metadata file not found: {self.metadata_path}"
            )

        self.index = faiss.read_index(str(self.index_path))

        with open(self.metadata_path, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

        if self.index.ntotal != len(self.metadata):
            raise RuntimeError(
                f"FAISS/metadata mismatch: "
                f"{self.index.ntotal} vectors vs "
                f"{len(self.metadata)} metadata records"
            )

    def search_image(
        self,
        image: Image.Image,
        top_k: int = 10,
    ) -> list[dict]:
        """
        Search the indexed archive using an input image.
        """

        if top_k < 1:
            raise ValueError("top_k must be >= 1")

        top_k = min(top_k, self.index.ntotal)

        embedding = self.encoder.encode_image(image)

        query = np.asarray(
            embedding,
            dtype=np.float32,
        ).reshape(1, -1)

        scores, indices = self.index.search(
            query,
            top_k,
        )

        results = []

        import re

        for rank, (score, idx) in enumerate(
            zip(scores[0], indices[0]),
            start=1,
        ):
            idx = int(idx)

            if idx < 0:
                continue

            record = dict(self.metadata[idx])
            
            # Extract actual acquisition date from Sentinel-1 filename
            if "source_tiff" in record and "acquisition_date" not in record:
                source_tiff = record["source_tiff"]
                match = re.search(r'_(\d{8})T', source_tiff)
                if match:
                    d_str = match.group(1)
                    record["acquisition_date"] = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:8]}"
                else:
                    record["acquisition_date"] = "Unknown"

            results.append(
                {
                    "rank": rank,
                    "score": float(score),
                    "record": record,
                }
            )

        return results

    def search_text(
        self,
        text: str,
        top_k: int = 10,
    ) -> list[dict]:
        """
        Search the indexed archive using natural language text.
        """

        if top_k < 1:
            raise ValueError("top_k must be >= 1")

        top_k = min(top_k, self.index.ntotal)

        embedding = self.encoder.encode_text(text)

        query = np.asarray(
            embedding,
            dtype=np.float32,
        ).reshape(1, -1)

        scores, indices = self.index.search(
            query,
            top_k,
        )

        results = []

        import re

        for rank, (score, idx) in enumerate(
            zip(scores[0], indices[0]),
            start=1,
        ):
            idx = int(idx)

            if idx < 0:
                continue

            record = dict(self.metadata[idx])
            
            # Extract actual acquisition date from Sentinel-1 filename
            if "source_tiff" in record and "acquisition_date" not in record:
                source_tiff = record["source_tiff"]
                match = re.search(r'_(\d{8})T', source_tiff)
                if match:
                    d_str = match.group(1)
                    record["acquisition_date"] = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:8]}"
                else:
                    record["acquisition_date"] = "Unknown"

            results.append(
                {
                    "rank": rank,
                    "score": float(score),
                    "record": record,
                }
            )

        return results

    def get_record_by_tile_id(self, tile_id: str) -> dict | None:
        """
        Safely retrieve a metadata record by its tile_id.
        """
        for record in self.metadata:
            if record.get("tile_id") == tile_id:
                return record
        return None

    def search_file(
        self,
        image_path: str | Path,
        top_k: int = 10,
    ) -> list[dict]:
        """
        Search the indexed archive using an image file.
        """

        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        with Image.open(image_path) as image:
            return self.search_image(
                image,
                top_k=top_k,
            )

    @classmethod
    def from_environment(
        cls,
        encoder: RetrievalEncoder,
    ) -> "RetrievalService":
        """
        Construct the retrieval service from environment variables.
        """

        index_path = os.environ.get("RETRIEVAL_INDEX_PATH")
        metadata_path = os.environ.get("RETRIEVAL_METADATA_PATH")

        if not index_path:
            raise RuntimeError(
                "RETRIEVAL_INDEX_PATH is not configured."
            )

        if not metadata_path:
            raise RuntimeError(
                "RETRIEVAL_METADATA_PATH is not configured."
            )

        return cls(
            encoder=encoder,
            index_path=index_path,
            metadata_path=metadata_path,
        )
