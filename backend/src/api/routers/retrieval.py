from __future__ import annotations

import importlib
import os
from functools import lru_cache

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

from pydantic import BaseModel, Field

from src.api.services.retrieval_encoder import RetrievalEncoder
from src.api.services.retrieval_service import RetrievalService

class TextSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Natural language query")
    top_k: int = Field(10, ge=1, le=100, description="Number of results to retrieve")


router = APIRouter(
    prefix="/retrieval",
    tags=["retrieval"],
)


@lru_cache(maxsize=1)
def get_retrieval_service() -> RetrievalService:
    """
    Create and cache the retrieval service.

    The RemoteCLIP model and FAISS index are loaded once
    and reused across requests.
    """

    encoder = RetrievalEncoder(
        os.environ["RETRIEVAL_MODEL_PATH"]
    )

    return RetrievalService.from_environment(
        encoder
    )


@router.post("/image-search")
async def image_search(
    image: UploadFile = File(...),
    top_k: int = 10,
):
    """
    Search the indexed satellite-image archive using
    an uploaded image.
    """

    if top_k < 1 or top_k > 100:
        raise HTTPException(
            status_code=400,
            detail="top_k must be between 1 and 100.",
        )

    try:
        contents = await image.read()

        if not contents:
            raise HTTPException(
                status_code=400,
                detail="Uploaded image is empty.",
            )

        from io import BytesIO

        pil_image = Image.open(
            BytesIO(contents)
        ).convert("RGB")

    except UnidentifiedImageError:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is not a valid image.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to read uploaded image: {exc}",
        )

    try:
        service = get_retrieval_service()

        results = service.search_image(
            pil_image,
            top_k=top_k,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Retrieval failed: {exc}",
        )

    return {
        "query": {
            "filename": image.filename,
            "content_type": image.content_type,
        },
        "model": {
            "name": service.encoder.MODEL_NAME,
            "version": service.encoder.MODEL_VERSION,
            "dimension": service.encoder.EMBEDDING_DIMENSION,
            "metric": "cosine",
        },
        "results": results,
        "count": len(results),
    }

@router.post("/text-search")
async def text_search(request: TextSearchRequest):
    """
    Search the indexed satellite-image archive using
    a natural language text query.
    """
    
    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=400,
            detail="Query text cannot be empty.",
        )

    try:
        service = get_retrieval_service()

        results = service.search_text(
            request.query,
            top_k=request.top_k,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Retrieval failed: {exc}",
        )

    return {
        "query": {
            "text": request.query,
        },
        "model": {
            "name": service.encoder.MODEL_NAME,
            "version": service.encoder.MODEL_VERSION,
            "dimension": service.encoder.EMBEDDING_DIMENSION,
            "metric": "cosine",
        },
        "results": results,
        "count": len(results),
    }

@router.get("/tile/{tile_id}")
async def get_tile_image(tile_id: str):
    """
    Safely serve a retrieval tile image by its tile_id.
    """
    try:
        service = get_retrieval_service()
        record = service.get_record_by_tile_id(tile_id)

        if not record:
            raise HTTPException(status_code=404, detail="Tile not found.")

        image_path = record.get("image_path")
        if not image_path or not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail="Image file not found.")

        return FileResponse(
            path=image_path,
            media_type="image/png"
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to serve tile: {exc}",
        )


