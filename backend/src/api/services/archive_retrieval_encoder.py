from __future__ import annotations

from pathlib import Path

import numpy as np
import open_clip
import torch

from src.api.services.archive_tiler import ArchiveTile


class ArchiveRetrievalEncoder:
    """
    RemoteCLIP encoder for production archive tiles.

    Input:
        ArchiveTile objects containing 224x224 RGB images.

    Output:
        L2-normalized float32 embeddings with dimension 1024.
    """

    MODEL_NAME = "RemoteCLIP-RN50"
    MODEL_VERSION = "RemoteCLIP-RN50"
    EMBEDDING_DIMENSION = 1024

    def __init__(
        self,
        checkpoint_path: str | Path,
    ) -> None:

        self.checkpoint_path = Path(
            checkpoint_path
        )

        if not self.checkpoint_path.exists():
            raise FileNotFoundError(
                f"RemoteCLIP checkpoint not found: "
                f"{self.checkpoint_path}"
            )

        self.device = (
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

        print(
            "Archive retrieval encoder device:",
            self.device,
        )

        self.model, _, self.preprocess = (
            open_clip.create_model_and_transforms(
                "RN50",
                pretrained=None,
            )
        )

        checkpoint = torch.load(
            self.checkpoint_path,
            map_location="cpu",
        )

        state_dict = {
            key: value
            for key, value in checkpoint.items()
            if not key.startswith("logit_scale")
        }

        result = self.model.load_state_dict(
            state_dict,
            strict=False,
        )

        if result.missing_keys != [
            "logit_scale"
        ]:
            raise RuntimeError(
                "Unexpected RemoteCLIP missing keys: "
                f"{result.missing_keys}"
            )

        if result.unexpected_keys:
            raise RuntimeError(
                "Unexpected RemoteCLIP checkpoint keys: "
                f"{result.unexpected_keys}"
            )

        self.model.to(self.device)
        self.model.eval()

        print(
            "RemoteCLIP checkpoint loaded:",
            self.checkpoint_path,
        )

    def encode_tiles(
        self,
        tiles: list[ArchiveTile],
        batch_size: int = 8,
    ) -> np.ndarray:
        """
        Encode archive tiles into normalized embeddings.

        Returns:
            numpy array with shape:
                (number_of_tiles, 1024)
        """

        if not tiles:
            raise ValueError(
                "tiles cannot be empty."
            )

        if batch_size < 1:
            raise ValueError(
                "batch_size must be >= 1."
            )

        tensors = []

        for tile in tiles:

            if tile.image.size != (
                224,
                224,
            ):
                raise ValueError(
                    f"Tile {tile.tile_id} has "
                    f"invalid size {tile.image.size}; "
                    "expected (224, 224)."
                )

            image_tensor = self.preprocess(
                tile.image
            )

            tensors.append(
                image_tensor
            )

        embeddings = []

        with torch.no_grad():

            for start in range(
                0,
                len(tensors),
                batch_size,
            ):

                batch_tensors = torch.stack(
                    tensors[start:start + batch_size]
                ).to(self.device)

                batch_embeddings = (
                    self.model.encode_image(
                        batch_tensors
                    )
                )

                batch_embeddings = (
                    batch_embeddings
                    / batch_embeddings.norm(
                        dim=-1,
                        keepdim=True,
                    )
                )

                embeddings.append(
                    batch_embeddings
                    .cpu()
                    .numpy()
                    .astype(
                        np.float32
                    )
                )

        result = np.concatenate(
            embeddings,
            axis=0,
        )

        if result.shape != (
            len(tiles),
            self.EMBEDDING_DIMENSION,
        ):
            raise RuntimeError(
                "Unexpected embedding shape: "
                f"{result.shape}; expected "
                f"({len(tiles)}, "
                f"{self.EMBEDDING_DIMENSION})"
            )

        # Final normalization check.
        norms = np.linalg.norm(
            result,
            axis=1,
        )

        if not np.allclose(
            norms,
            1.0,
            atol=1e-5,
        ):
            raise RuntimeError(
                "One or more embeddings are "
                "not L2 normalized."
            )

        return result


__all__ = [
    "ArchiveRetrievalEncoder",
]