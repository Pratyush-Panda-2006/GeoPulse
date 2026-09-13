from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_
from pyproj import Transformer

from src.api import db
from src.api.models import SARScene, SARAsset


router = APIRouter(
    prefix="/timeline",
    tags=["timeline"],
)


class TimelineAsset(BaseModel):
    id: int
    asset_key: Optional[str] = None
    time_label: str
    storage_key: str
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    band_count: Optional[int] = None
    bands: Optional[str] = None
    crs: Optional[str] = None


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


class TimelineResponse(BaseModel):
    observations: list[TimelineObservation]
    count: int


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

            observation_assets = [
                TimelineAsset(
                    id=asset.id,
                    asset_key=asset.asset_key,
                    time_label=asset.time_label,
                    storage_key=asset.storage_key,
                    mime_type=asset.mime_type,
                    width=asset.width,
                    height=asset.height,
                    band_count=asset.band_count,
                    bands=asset.bands,
                    crs=asset.crs,
                )
                for asset in assets
            ]

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