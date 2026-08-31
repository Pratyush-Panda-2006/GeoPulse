from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
import datetime as dt

from src.api import db
from src.api.models import SARRequest, SARAsset, SARScene
from src.api.schemas import DetectSentinelRequest
from src.data_ingestion.sar_asset_records import create_asset_record
from src.data_ingestion.sar_ingestion import fetch_sar_pair_raw
from src.data_ingestion.sar_storage import store_sar_pair
from src.storage.object_storage import download_bytes

router = APIRouter(
    prefix="/requests",
    tags=["SAR Requests"],
)

def get_or_create_scene(session: Session, meta: dict) -> SARScene:
    scene = session.query(SARScene).filter_by(
        provider=meta["provider"],
        scene_id=meta["scene_id"]
    ).first()
    
    if not scene:
        acq_date = dt.datetime.fromisoformat(meta["acquisition_date"].replace("Z", "+00:00"))
        bbox = meta.get("bbox")
        
        scene = SARScene(
            provider=meta["provider"],
            scene_id=meta["scene_id"],
            acquisition_date=acq_date,
            bbox_min_lon=bbox[0] if bbox else None,
            bbox_min_lat=bbox[1] if bbox else None,
            bbox_max_lon=bbox[2] if bbox else None,
            bbox_max_lat=bbox[3] if bbox else None,
            status="created"
        )
        session.add(scene)
        session.commit()
        session.refresh(scene)
        
    return scene


@router.post(
    "",
    summary="Create and ingest a SAR request",
)
async def create_sar_request(
    payload: DetectSentinelRequest,
):
    """
    Create a SAR request, fetch T1/T2 from CDSE, store the raw TIFFs,
    and create the corresponding sar_assets records.
    """

    db.init_db()

    if db.SessionLocal is None:
        raise HTTPException(
            status_code=500,
            detail="Database is not configured",
        )

    session: Session = db.SessionLocal()
    request = None

    try:
        # ── Create request record ──────────────────────────────────────────
        request = SARRequest(
            bbox_min_lon=payload.bbox.min_lon,
            bbox_min_lat=payload.bbox.min_lat,
            bbox_max_lon=payload.bbox.max_lon,
            bbox_max_lat=payload.bbox.max_lat,
            t1_date_from=payload.date_range_t1[0],
            t1_date_to=payload.date_range_t1[1],
            t2_date_from=payload.date_range_t2[0],
            t2_date_to=payload.date_range_t2[1],
            resolution_width=payload.resolution[0],
            resolution_height=payload.resolution[1],
            status="created",
        )

        session.add(request)
        session.commit()
        session.refresh(request)

        request_id = request.id

        # ── Fetch raw T1/T2 from CDSE ─────────────────────────────────────
        t1_bytes, t2_bytes, t1_meta, t2_meta = fetch_sar_pair_raw(
            bbox=payload.bbox.to_list(),
            date_t1_range=payload.date_range_t1,
            date_t2_range=payload.date_range_t2,
            output_resolution=payload.resolution,
        )

        # ── Create or reuse scenes ────────────────────────────────────────
        t1_scene = get_or_create_scene(session, t1_meta)
        t2_scene = get_or_create_scene(session, t2_meta)

        # ── Upload raw TIFFs to Object Storage ────────────────────────────
        t1_storage, t2_storage = store_sar_pair(
            request_id=request_id,
            t1_bytes=t1_bytes,
            t2_bytes=t2_bytes,
        )

        # ── Extract metadata and create asset records ──────────────────────
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            t1_path = temp_path / "T1.tif"
            t2_path = temp_path / "T2.tif"

            t1_path.write_bytes(t1_bytes)
            t2_path.write_bytes(t2_bytes)

            t1_asset = create_asset_record(
                db=session,
                request_id=request_id,
                time_label="T1",
                storage_key=t1_storage["storage_key"],
                local_tiff_path=t1_path,
                scene_id=t1_scene.id,
                asset_key=f"T1_{request_id}_{t1_scene.id}"
            )

            t2_asset = create_asset_record(
                db=session,
                request_id=request_id,
                time_label="T2",
                storage_key=t2_storage["storage_key"],
                local_tiff_path=t2_path,
                scene_id=t2_scene.id,
                asset_key=f"T2_{request_id}_{t2_scene.id}"
            )

        # ── Mark request completed ────────────────────────────────────────
        request.status = "completed"
        session.commit()

        return {
            "status": "completed",
            "request_id": request_id,
            "assets": [
                {
                    "id": t1_asset.id,
                    "time_label": t1_asset.time_label,
                    "storage_key": t1_asset.storage_key,
                    "file_size_bytes": t1_asset.file_size_bytes,
                    "checksum_sha256": t1_asset.checksum_sha256,
                    "width": t1_asset.width,
                    "height": t1_asset.height,
                    "band_count": t1_asset.band_count,
                    "bands": t1_asset.bands,
                    "crs": t1_asset.crs,
                },
                {
                    "id": t2_asset.id,
                    "time_label": t2_asset.time_label,
                    "storage_key": t2_asset.storage_key,
                    "file_size_bytes": t2_asset.file_size_bytes,
                    "checksum_sha256": t2_asset.checksum_sha256,
                    "width": t2_asset.width,
                    "height": t2_asset.height,
                    "band_count": t2_asset.band_count,
                    "bands": t2_asset.bands,
                    "crs": t2_asset.crs,
                },
            ],
        }

    except Exception as exc:
        session.rollback()

        if request is not None:
            try:
                request.status = "failed"
                request.error_message = str(exc)
                session.commit()
            except Exception:
                session.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"SAR ingestion failed: {exc}",
        ) from exc

    finally:
        session.close()


@router.get(
    "/{request_id}",
    summary="Get SAR request and assets",
)
async def get_sar_request(request_id: int):
    """
    Return a SAR request together with its T1/T2 asset metadata.
    """

    db.init_db()

    if db.SessionLocal is None:
        raise HTTPException(
            status_code=500,
            detail="Database is not configured",
        )

    session = db.SessionLocal()

    try:
        request = (
            session.query(SARRequest)
            .filter(SARRequest.id == request_id)
            .first()
        )

        if request is None:
            raise HTTPException(
                status_code=404,
                detail=f"SAR request {request_id} not found",
            )

        assets = (
            session.query(SARAsset)
            .filter(SARAsset.request_id == request_id)
            .order_by(SARAsset.time_label)
            .all()
        )

        return {
            "request_id": request.id,
            "status": request.status,
            "bbox": [
                request.bbox_min_lon,
                request.bbox_min_lat,
                request.bbox_max_lon,
                request.bbox_max_lat,
            ],
            "date_range_t1": [
                str(request.t1_date_from),
                str(request.t1_date_to),
            ],
            "date_range_t2": [
                str(request.t2_date_from),
                str(request.t2_date_to),
            ],
            "resolution": [
                request.resolution_width,
                request.resolution_height,
            ],
            "assets": [
                {
                    "id": asset.id,
                    "time_label": asset.time_label,
                    "storage_key": asset.storage_key,
                    "mime_type": asset.mime_type,
                    "file_size_bytes": asset.file_size_bytes,
                    "checksum_sha256": asset.checksum_sha256,
                    "width": asset.width,
                    "height": asset.height,
                    "band_count": asset.band_count,
                    "bands": asset.bands,
                    "crs": asset.crs,
                }
                for asset in assets
            ],
        }

    finally:
        session.close()