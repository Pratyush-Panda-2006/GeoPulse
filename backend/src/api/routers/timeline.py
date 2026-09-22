from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_
from pyproj import Transformer

from src.api import db
from src.api.models import SARScene, SARAsset, SARSceneAsset
import time
import hashlib
from src.api.schemas import ChangeDetectionResponse
from src.api.services.inference_service import run_change_detection
from src.preprocessing.sar_loader import load_sar_pair_for_inference, extract_geotiff_metadata
from src.storage.object_storage import download_bytes
from src.data_ingestion.sentinel_client import SentinelHubClient, CDSEAuthManager
from src.api.services.archive_asset_service import fetch_scene_asset


router = APIRouter(
    prefix="/timeline",
    tags=["timeline"],
)


class TimelineAsset(BaseModel):
    id: int
    scene_asset_id: Optional[int] = None
    asset_key: Optional[str] = None
    time_label: str
    storage_key: str
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    band_count: Optional[int] = None
    bands: Optional[str] = None
    crs: Optional[str] = None
    has_georeference: Optional[bool] = None


class TimelineObservation(BaseModel):
    scene_id: int
    sentinel_scene_id: str
    acquisition_date: datetime
    provider: str
    bbox: list[float]
    crs: Optional[str] = None
    has_georeference: Optional[bool] = None
    status: str
    assets: list[TimelineAsset]



class ArchiveChangeDetectionRequest(BaseModel):
    before_asset_id: int
    after_asset_id: int
    threshold: float = Field(
        0.85,
        ge=0.0,
        le=1.0,
    )
    min_region_area_px: int = Field(
        100,
        ge=1,
    )

class TimelineResponse(BaseModel):
    observations: list[TimelineObservation]
    count: int

class ArchiveAssetRequest(BaseModel):
    scene_id: int
    bbox: list[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="AOI as [west, south, east, north] in EPSG:4326.",
    )
    output_width: int = Field(512, ge=64, le=2048)
    output_height: int = Field(512, ge=64, le=2048)


@router.get("", response_model=TimelineResponse)
def get_timeline(
    min_lon: float = Query(...),
    min_lat: float = Query(...),
    max_lon: float = Query(...),
    max_lat: float = Query(...),
    crs: str = Query("EPSG:4326"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
):
    """
    Return chronological SAR observations whose scene footprint
    intersects the requested AOI.
    """

    if min_lon >= max_lon or min_lat >= max_lat:
        raise HTTPException(
            status_code=400,
            detail="Invalid AOI: minimum coordinates must be less than maximum coordinates.",
        )

    try:
        transformer = Transformer.from_crs(
            crs,
            "EPSG:4326",
            always_xy=True,
        )

        x1, y1 = transformer.transform(min_lon, min_lat)
        x2, y2 = transformer.transform(max_lon, max_lat)

        min_lon_4326 = min(x1, x2)
        max_lon_4326 = max(x1, x2)
        min_lat_4326 = min(y1, y2)
        max_lat_4326 = max(y1, y2)

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid CRS '{crs}': {exc}",
        ) from exc

    db.init_db()

    if db.SessionLocal is None:
        raise HTTPException(
            status_code=503,
            detail="Database is not configured.",
        )

    session = db.SessionLocal()

    try:
        filters = [
            SARScene.bbox_max_lon >= min_lon_4326,
            SARScene.bbox_min_lon <= max_lon_4326,
            SARScene.bbox_max_lat >= min_lat_4326,
            SARScene.bbox_min_lat <= max_lat_4326,
        ]

        if start_date is not None:
            filters.append(SARScene.acquisition_date >= start_date)

        if end_date is not None:
            filters.append(SARScene.acquisition_date <= end_date)

        scenes = (
            session.query(SARScene)
            .filter(and_(*filters))
            .order_by(SARScene.acquisition_date.asc())
            .all()
        )

        observations = []

        for scene in scenes:
            assets = (
                session.query(SARAsset)
                .filter(SARAsset.scene_id == scene.id)
                .order_by(SARAsset.id.asc())
                .all()
            )
            
            scene_assets = (
                session.query(SARSceneAsset)
                .filter(SARSceneAsset.scene_id == scene.id)
                .order_by(SARSceneAsset.id.asc())
                .all()
            )

            observation_assets = [
                TimelineAsset(
                    id=asset.id,
                    scene_asset_id=None,
                    asset_key=asset.asset_key,
                    time_label=asset.time_label,
                    storage_key=asset.storage_key,
                    mime_type=asset.mime_type,
                    width=asset.width,
                    height=asset.height,
                    band_count=asset.band_count,
                    bands=asset.bands,
                    crs=asset.crs,
                    has_georeference=None,
                )
                for asset in assets
            ]
            
            observation_assets.extend([
                TimelineAsset(
                    id=asset.id,
                    scene_asset_id=asset.id,
                    asset_key=None,
                    time_label="ARCHIVE",
                    storage_key=asset.storage_key,
                    mime_type=asset.mime_type,
                    width=asset.width,
                    height=asset.height,
                    band_count=asset.band_count,
                    bands=asset.bands,
                    crs=asset.crs,
                    has_georeference=asset.has_georeference,
                )
                for asset in scene_assets
            ])

            observations.append(
                TimelineObservation(
                    scene_id=scene.id,
                    sentinel_scene_id=scene.scene_id,
                    acquisition_date=scene.acquisition_date,
                    provider=scene.provider,
                    bbox=[
                        scene.bbox_min_lon,
                        scene.bbox_min_lat,
                        scene.bbox_max_lon,
                        scene.bbox_max_lat,
                    ],
                    crs=scene.crs,
                    has_georeference=scene.has_georeference,
                    status=scene.status,
                    assets=observation_assets,
                )
            )

        return TimelineResponse(
            observations=observations,
            count=len(observations),
        )

    finally:
        session.close()

@router.post(
    "/archive-asset",
    summary="Archive a Sentinel-1 scene tile for a requested AOI",
)
async def archive_timeline_asset(request: ArchiveAssetRequest):
    db.init_db()

    if db.SessionLocal is None:
        raise HTTPException(
            status_code=503,
            detail="Database is not configured.",
        )

    west, south, east, north = request.bbox

    if west >= east or south >= north:
        raise HTTPException(
            status_code=400,
            detail="Invalid bbox: expected [west, south, east, north].",
        )

    session = db.SessionLocal()

    try:
        scene = (
            session.query(SARScene)
            .filter(SARScene.id == request.scene_id)
            .first()
        )

        if scene is None:
            raise HTTPException(
                status_code=404,
                detail=f"SAR scene {request.scene_id} does not exist.",
            )

        if scene.provider != "CDSE":
            raise HTTPException(
                status_code=400,
                detail="Only CDSE scenes can be archived through this endpoint.",
            )

        if not scene.scene_id.startswith("S1"):
            raise HTTPException(
                status_code=400,
                detail="Only Sentinel-1 scenes can be archived through this endpoint.",
            )

        sentinel_client = SentinelHubClient(CDSEAuthManager())

        asset = fetch_scene_asset(
            db=session,
            sentinel_client=sentinel_client,
            scene=scene,
            bbox=request.bbox,
            output_resolution=(
                request.output_width,
                request.output_height,
            ),
        )

        return {
            "status": "success",
            "scene_id": scene.id,
            "sentinel_scene_id": scene.scene_id,
            "acquisition_date": scene.acquisition_date,
            "provider": scene.provider,
            "asset": {
                "id": asset.id,
                "scene_asset_id": asset.id,
                "storage_key": asset.storage_key,
                "mime_type": asset.mime_type,
                "width": asset.width,
                "height": asset.height,
                "band_count": asset.band_count,
                "bands": asset.bands,
                "crs": asset.crs,
                "has_georeference": asset.has_georeference,
                "file_size_bytes": asset.file_size_bytes,
                "checksum_sha256": asset.checksum_sha256,
                "bbox": [
                    asset.bbox_min_lon,
                    asset.bbox_min_lat,
                    asset.bbox_max_lon,
                    asset.bbox_max_lat,
                ],
            },
        }

    except HTTPException:
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(
            status_code=502,
            detail=f"Failed to archive Sentinel-1 scene: {exc}",
        ) from exc
    finally:
        session.close()

@router.post(
    "/change-detection",
    response_model=ChangeDetectionResponse,
    summary="Change Detection Between Archived Sentinel-1 Assets",
)
async def detect_archive_change(request: ArchiveChangeDetectionRequest):
    t0 = time.perf_counter()
    
    db.init_db()
    if db.SessionLocal is None:
        raise HTTPException(status_code=503, detail="Database is not configured.")
        
    session = db.SessionLocal()
    try:
        before_asset = session.query(SARSceneAsset).get(request.before_asset_id)
        after_asset = session.query(SARSceneAsset).get(request.after_asset_id)
        
        if not before_asset or not after_asset:
            raise HTTPException(status_code=404, detail="One or both SARSceneAsset records do not exist.")
            
        before_scene = session.query(SARScene).get(before_asset.scene_id)
        after_scene = session.query(SARScene).get(after_asset.scene_id)
        
        if not before_scene or not after_scene:
            raise HTTPException(status_code=404, detail="One or both SARScene records do not exist.")
            
        if not before_asset.storage_key or not after_asset.storage_key:
            raise HTTPException(status_code=400, detail="Both assets must have a storage_key.")
        if not before_asset.has_georeference or not after_asset.has_georeference:
            raise HTTPException(status_code=400, detail="Both assets must have georeferencing.")
        if before_scene.provider != "CDSE" or after_scene.provider != "CDSE":
            raise HTTPException(status_code=400, detail="Both scenes must come from CDSE.")
        if not before_scene.scene_id.startswith("S1") or not after_scene.scene_id.startswith("S1"):
            raise HTTPException(status_code=400, detail="Both scenes must be Sentinel-1 scenes.")
        if before_asset.band_count != 2 or after_asset.band_count != 2:
            raise HTTPException(status_code=400, detail="Both assets must have exactly 2 bands.")
            
        before_bytes = download_bytes(before_asset.storage_key)
        after_bytes = download_bytes(after_asset.storage_key)
        
        if before_asset.checksum_sha256:
            if hashlib.sha256(before_bytes).hexdigest() != before_asset.checksum_sha256:
                raise HTTPException(status_code=422, detail="Before asset checksum mismatch.")
        if after_asset.checksum_sha256:
            if hashlib.sha256(after_bytes).hexdigest() != after_asset.checksum_sha256:
                raise HTTPException(status_code=422, detail="After asset checksum mismatch.")
                
        after_geo_meta = extract_geotiff_metadata(after_bytes)
        transform = after_geo_meta.get("transform")
        crs = after_geo_meta.get("crs")
        
        if transform is None or crs is None:
            raise HTTPException(status_code=422, detail="After asset is missing transform or CRS.")
            
        t1_np, t2_np = load_sar_pair_for_inference(
            before_bytes,
            after_bytes,
            is_linear=True,
            return_tensors=False,
        )
        
        result = run_change_detection(
            t1_np=t1_np,
            t2_np=t2_np,
            model_name="snunet_cd_sar",
            threshold=request.threshold,
            min_region_area_px=request.min_region_area_px,
            bbox=[
                after_asset.bbox_min_lon,
                after_asset.bbox_min_lat,
                after_asset.bbox_max_lon,
                after_asset.bbox_max_lat,
            ],
            transform=transform,
            crs=crs,
        )
        
        elapsed = round(time.perf_counter() - t0, 3)
        
        return ChangeDetectionResponse(
            status="success",
            model_used="snunet_cd_sar",
            threshold=request.threshold,
            total_pixels=result.total_pixels,
            changed_pixels=result.changed_pixels,
            change_percentage=result.change_percentage,
            total_changed_area_sq_km=result.total_changed_area_sq_km,
            num_change_clusters=result.num_change_clusters,
            regions=result.regions,
            t1_preview_base64=result.t1_preview_base64,
            t2_preview_base64=result.t2_preview_base64,
            t1_grayscale_base64=result.t1_grayscale_base64,
            t2_grayscale_base64=result.t2_grayscale_base64,
            t1_false_color_base64=result.t1_false_color_base64,
            t2_false_color_base64=result.t2_false_color_base64,
            change_mask_base64=result.change_mask_base64,
            confidence_heatmap_base64=result.confidence_heatmap_base64,
            overlay_base64=result.overlay_base64,
            change_boxes_base64=result.change_boxes_base64,
            execution_time_sec=elapsed,
            
            before_asset_id=before_asset.id,
            after_asset_id=after_asset.id,
            before_scene_id=before_scene.id,
            after_scene_id=after_scene.id,
            before_sentinel_scene_id=before_scene.scene_id,
            after_sentinel_scene_id=after_scene.scene_id,
            before_acquisition_date=before_scene.acquisition_date,
            after_acquisition_date=after_scene.acquisition_date,
            before_storage_key=before_asset.storage_key,
            after_storage_key=after_asset.storage_key,
            before_checksum_sha256=before_asset.checksum_sha256,
            after_checksum_sha256=after_asset.checksum_sha256,
        )
        
    finally:
        session.close()
