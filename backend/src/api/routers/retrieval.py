from __future__ import annotations

import os
from functools import lru_cache
from io import BytesIO

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

from src.api.services.retrieval_encoder import RetrievalEncoder
from src.api.services.retrieval_service import RetrievalService
from src.api.services.archive_retrieval_encoder import ArchiveRetrievalEncoder
from src.api.services.production_archive_retrieval_service import (
    ProductionArchiveRetrievalService,
)


class TextSearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural language query",
    )
    top_k: int = Field(
        10,
        ge=1,
        le=100,
        description="Number of results to retrieve",
    )


router = APIRouter(
    prefix="/retrieval",
    tags=["retrieval"],
)


# ============================================================
# EXISTING EXPERIMENTAL RETRIEVAL
# ============================================================

@lru_cache(maxsize=1)
def get_retrieval_service() -> RetrievalService:
    """
    Create and cache the existing experimental retrieval service.
    """

    encoder = RetrievalEncoder(
        os.environ["RETRIEVAL_MODEL_PATH"]
    )

    return RetrievalService.from_environment(
        encoder
    )


# ============================================================
# PRODUCTION ARCHIVE RETRIEVAL
# ============================================================

@lru_cache(maxsize=1)
def get_production_archive_service() -> ProductionArchiveRetrievalService:
    """
    Create and cache the production Sentinel-1 archive
    retrieval service.

    The RemoteCLIP model and FAISS index are loaded once
    and reused across requests.
    """

    checkpoint_path = os.environ.get(
        "ARCHIVE_RETRIEVAL_MODEL_PATH"
    )

    if not checkpoint_path:
        raise RuntimeError(
            "ARCHIVE_RETRIEVAL_MODEL_PATH "
            "is not configured."
        )

    encoder = ArchiveRetrievalEncoder(
        checkpoint_path
    )

    return ProductionArchiveRetrievalService.from_environment(
        encoder
    )


# ============================================================
# EXISTING IMAGE SEARCH
# ============================================================

@router.post("/image-search")
async def image_search(
    image: UploadFile = File(...),
    top_k: int = 10,
):
    """
    Search the existing indexed satellite-image archive
    using an uploaded image.
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


# ============================================================
# EXISTING TEXT SEARCH
# ============================================================

@router.post("/text-search")
async def text_search(
    request: TextSearchRequest,
):
    """
    Search the existing indexed satellite-image archive
    using a natural language text query.
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


# ============================================================
# PRODUCTION ARCHIVE IMAGE SEARCH
# ============================================================

@router.post("/archive-image-search")
async def archive_image_search(
    image: UploadFile = File(...),
    top_k: int = 10,
):
    """
    Search the production Sentinel-1 archive using
    an uploaded satellite image.
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
        service = get_production_archive_service()

        results = service.search_image(
            pil_image,
            top_k=top_k,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Production archive retrieval failed: {exc}",
        )

    return {
        "query": {
            "filename": image.filename,
            "content_type": image.content_type,
        },
        "archive": {
            "type": "sentinel-1",
            "index_vectors": service.count,
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


# ============================================================
# PRODUCTION ARCHIVE TEXT SEARCH
# ============================================================

@router.post("/archive-text-search")
async def archive_text_search(
    request: TextSearchRequest,
):
    """
    Search the production Sentinel-1 archive using
    a natural language query.
    """

    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=400,
            detail="Query text cannot be empty.",
        )

    try:
        service = get_production_archive_service()

        results = service.search_text(
            request.query,
            top_k=request.top_k,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Production archive retrieval failed: {exc}",
        )

    return {
        "query": {
            "text": request.query,
        },
        "archive": {
            "type": "sentinel-1",
            "index_vectors": service.count,
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


# ============================================================
# EXISTING TILE ENDPOINT
# ============================================================

@router.get("/tile/{tile_id}")
async def get_tile_image(
    tile_id: str,
):
    """
    Safely serve an existing retrieval tile image
    by its tile_id.
    """

    try:
        service = get_retrieval_service()

        record = service.get_record_by_tile_id(
            tile_id
        )

        if not record:
            raise HTTPException(
                status_code=404,
                detail="Tile not found.",
            )

        image_path = record.get(
            "image_path"
        )

        if not image_path or not os.path.exists(
            image_path
        ):
            raise HTTPException(
                status_code=404,
                detail="Image file not found.",
            )

        return FileResponse(
            path=image_path,
            media_type="image/png",
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to serve tile: {exc}",
        )