from fastapi import APIRouter, HTTPException, Query, Response
import logging

from src.data_ingestion.sentinel_client import SentinelHubClient, CDSEAuthManager, SentinelAPIError

router = APIRouter(prefix="/terrain", tags=["Terrain"])
logger = logging.getLogger(__name__)

@router.get("", response_class=Response)
async def get_terrain(
    west: float = Query(..., ge=-180.0, le=180.0, description="Western longitude"),
    south: float = Query(..., ge=-90.0, le=90.0, description="Southern latitude"),
    east: float = Query(..., ge=-180.0, le=180.0, description="Eastern longitude"),
    north: float = Query(..., ge=-90.0, le=90.0, description="Northern latitude"),
    width: int = Query(512, gt=0, le=2048, description="Output image width in pixels"),
    height: int = Query(512, gt=0, le=2048, description="Output image height in pixels"),
):
    """
    Fetch a Copernicus DEM GLO-30 tile as raw GeoTIFF bytes.
    """
    if west >= east:
        raise HTTPException(status_code=400, detail="west must be less than east")
    if south >= north:
        raise HTTPException(status_code=400, detail="south must be less than north")

    bbox = [west, south, east, north]
    output_resolution = (width, height)

    try:
        # Instantiate/reuse SentinelHubClient auth mechanism
        auth = CDSEAuthManager()
        client = SentinelHubClient(auth)

        logger.info(f"Fetching DEM tile for bbox={bbox} res={output_resolution}")
        dem_bytes = client.fetch_dem_tile(bbox=bbox, output_resolution=output_resolution)

        return Response(content=dem_bytes, media_type="image/tiff")
    except SentinelAPIError as e:
        logger.error(f"Sentinel API Error fetching DEM: {e}")
        raise HTTPException(status_code=502, detail=f"Upstream Sentinel API Error: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to fetch DEM: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while fetching DEM")
