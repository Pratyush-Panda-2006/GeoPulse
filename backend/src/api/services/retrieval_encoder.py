from __future__ import annotations

import os
from pathlib import Path
from threading import Lock

import numpy as np
import torch
import open_clip
from PIL import Image


class RetrievalEncoder:
    """
    GeoPulse image retrieval encoder using RemoteCLIP-RN50.

    Input:
        RGB PIL image

    Output:
        L2-normalized 1024-dimensional float32 embedding.
    """

    MODEL_NAME = "RemoteCLIP-RN50"
    MODEL_VERSION = "RemoteCLIP-RN50"
    EMBEDDING_DIMENSION = 1024

    def __init__(
        self,
        checkpoint_path: str | Path,
    ) -> None:
        self.checkpoint_path = Path(checkpoint_path)

        if not self.checkpoint_path.exists():
            raise FileNotFoundError(
                f"RemoteCLIP checkpoint not found: {self.checkpoint_path}"
            )

        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        self._lock = Lock()

        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            "RN50",
            pretrained=str(self.checkpoint_path),
        )

        self.model = self.model.to(self.device)
        self.model.eval()

    def encode_image(self, image: Image.Image) -> np.ndarray:
        """
        Encode one RGB image.

        Returns:
            float32 NumPy array with shape (1024,)
            and L2 norm approximately 1.0.
        """

        if not isinstance(image, Image.Image):
            raise TypeError(
                f"Expected PIL.Image.Image, got {type(image).__name__}"
            )

        image = image.convert("RGB")

        tensor = self.preprocess(image).unsqueeze(0).to(self.device)

        with self._lock:
            with torch.no_grad():
                embedding = self.model.encode_image(tensor)

        embedding = embedding / embedding.norm(
            dim=-1,
            keepdim=True,
        )

        result = (
            embedding[0]
            .detach()
            .cpu()
            .numpy()
            .astype(np.float32, copy=False)
        )

        if result.shape != (self.EMBEDDING_DIMENSION,):
            raise RuntimeError(
                f"Unexpected embedding shape: {result.shape}; "
                f"expected ({self.EMBEDDING_DIMENSION},)"
            )

        return result

    def encode_file(
        self,
        image_path: str | Path,
    ) -> np.ndarray:
        """
        Encode an RGB image file.
        """

        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        with Image.open(image_path) as image:
            return self.encode_image(image)

    def encode_text(self, text: str) -> np.ndarray:
        """
        Encode natural language text.

        Returns:
            float32 NumPy array with shape (1024,)
            and L2 norm approximately 1.0.
        """
        if not text or not text.strip():
            raise ValueError("Query text cannot be empty.")
            
        # tokenizer from open_clip
        tokens = open_clip.tokenize([text]).to(self.device)

        with self._lock:
            with torch.no_grad():
                embedding = self.model.encode_text(tokens)

        embedding = embedding / embedding.norm(
            dim=-1,
            keepdim=True,
        )

        result = (
            embedding[0]
            .detach()
            .cpu()
            .numpy()
            .astype(np.float32, copy=False)
        )

        if result.shape != (self.EMBEDDING_DIMENSION,):
            raise RuntimeError(
                f"Unexpected embedding shape: {result.shape}; "
                f"expected ({self.EMBEDDING_DIMENSION},)"
            )

        return result


def get_retrieval_encoder() -> RetrievalEncoder:
    """
    Construct the GeoPulse retrieval encoder using the
    RETRIEVAL_MODEL_PATH environment variable.
    """

    checkpoint = os.environ.get("RETRIEVAL_MODEL_PATH")

    if not checkpoint:
        raise RuntimeError(
            "RETRIEVAL_MODEL_PATH is not configured."
        )

    return RetrievalEncoder(checkpoint)
