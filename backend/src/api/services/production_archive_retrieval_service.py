from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import open_clip
from PIL import Image

from src.api.services.archive_index_manager import (
    ArchiveIndexManager,
)
from src.api.services.archive_retrieval_encoder import (
    ArchiveRetrievalEncoder,
)


class ProductionArchiveRetrievalService:
    """
    Retrieval service backed by the production Sentinel-1
    archive FAISS index.

    Unlike the experimental RetrievalService, this service
    reads the production archive index created by the
    incremental archive ingestion pipeline.
    """

    def __init__(
        self,
        encoder: ArchiveRetrievalEncoder,
        index_path: str | Path,
        metadata_path: str | Path,
    ) -> None:

        self.encoder = encoder

        self.index_manager = (
            ArchiveIndexManager(
                index_path=index_path,
                metadata_path=metadata_path,
            )
        )

    @property
    def count(self) -> int:
        return self.index_manager.count

    def search_image(
        self,
        image: Image.Image,
        top_k: int = 10,
    ) -> list[dict]:
        """
        Search the production archive using an image.
        """

        if top_k < 1:
            raise ValueError(
                "top_k must be >= 1."
            )

        if self.count == 0:
            return []

        top_k = min(
            top_k,
            self.count,
        )

        # The production archive stores 224x224
        # RGB tile representations. The RemoteCLIP
        # preprocessing handles the final model input size.
        image = image.convert("RGB")

        image_tensor = (
            self.encoder.preprocess(
                image
            )
        )

        import torch

        with torch.no_grad():

            tensor = (
                image_tensor
                .unsqueeze(0)
                .to(
                    self.encoder.device
                )
            )

            embedding = (
                self.encoder.model.encode_image(
                    tensor
                )
            )

            embedding = (
                embedding
                / embedding.norm(
                    dim=-1,
                    keepdim=True,
                )
            )

        query = (
            embedding
            .cpu()
            .numpy()
            .astype(np.float32)
        )

        return self.index_manager.search(
            query,
            top_k=top_k,
        )

    def search_text(
        self,
        text: str,
        top_k: int = 10,
    ) -> list[dict]:
        """
        Search the production archive using a natural-language
        text query through RemoteCLIP.
        """

        if not text or not text.strip():
            raise ValueError(
                "text query must not be empty."
            )

        if top_k < 1:
            raise ValueError(
                "top_k must be >= 1."
            )

        if self.count == 0:
            return []

        top_k = min(
            top_k,
            self.count,
        )

        import torch

        tokens = open_clip.tokenize(
            [text.strip()]
        ).to(
            self.encoder.device
        )

        with torch.no_grad():

            embedding = (
                self.encoder.model.encode_text(
                    tokens
                )
            )

            embedding = (
                embedding
                / embedding.norm(
                    dim=-1,
                    keepdim=True,
                )
            )

        query = (
            embedding
            .cpu()
            .numpy()
            .astype(np.float32)
        )

        return self.index_manager.search(
            query,
            top_k=top_k,
        )

    def search_file(
        self,
        image_path: str | Path,
        top_k: int = 10,
    ) -> list[dict]:
        """
        Search the production archive using an image file.
        """

        image_path = Path(
            image_path
        )

        if not image_path.exists():
            raise FileNotFoundError(
                f"Image not found: "
                f"{image_path}"
            )

        with Image.open(
            image_path
        ) as image:

            return self.search_image(
                image,
                top_k=top_k,
            )

    def get_record_by_tile_id(
        self,
        tile_id: str,
    ) -> dict | None:
        """
        Retrieve production metadata by tile ID.
        """

        for record in (
            self.index_manager.metadata
        ):

            if record.get(
                "tile_id"
            ) == tile_id:

                return dict(record)

        return None

    @classmethod
    def from_environment(
        cls,
        encoder: ArchiveRetrievalEncoder,
    ) -> "ProductionArchiveRetrievalService":
        """
        Construct the production archive retrieval
        service from environment variables.
        """

        index_path = os.environ.get(
            "ARCHIVE_RETRIEVAL_INDEX_PATH"
        )

        metadata_path = os.environ.get(
            "ARCHIVE_RETRIEVAL_METADATA_PATH"
        )

        if not index_path:
            raise RuntimeError(
                "ARCHIVE_RETRIEVAL_INDEX_PATH "
                "is not configured."
            )

        if not metadata_path:
            raise RuntimeError(
                "ARCHIVE_RETRIEVAL_METADATA_PATH "
                "is not configured."
            )

        return cls(
            encoder=encoder,
            index_path=index_path,
            metadata_path=metadata_path,
        )


__all__ = [
    "ProductionArchiveRetrievalService",
]