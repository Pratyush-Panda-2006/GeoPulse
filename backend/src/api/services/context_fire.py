import logging
import os
import io
import csv
import functools
import urllib.request
import urllib.error
from datetime import datetime, timedelta
import math
from typing import Dict, List
from src.api.schemas import ChangedRegion

logger = logging.getLogger(__name__)

FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
MAX_DAYS_PER_REQUEST = 10

def _haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    # Radius of earth in km
    R = 6371.0
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

@functools.lru_cache(maxsize=128)
def _fetch_firms_chunk(map_key: str, source: str, bbox_str: str, duration: int, date_str: str) -> List[dict]:
    url = f"{FIRMS_BASE_URL}/{map_key}/{source}/{bbox_str}/{duration}/{date_str}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            content = response.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            return list(reader)
    except urllib.error.URLError as e:
        logger.warning(f"FIRMS fetch failed for {source} on {date_str}: {e}")
        return []

def get_fire_context(
    regions: List[ChangedRegion], 
    bbox: List[float], 
    start_date: str, 
    end_date: str
) -> Dict[int, dict]:
    """
    Fetch NASA FIRMS hotspots for the AOI in <= 10 day chunks.
    Match hotspots to ChangedRegions.
    """
    map_key = os.environ.get("NASA_FIRMS_MAP_KEY")
    if not map_key:
        logger.warning("NASA_FIRMS_MAP_KEY not set. Skipping fire context.")
        return {}
        
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    now = datetime.now()
    
    bbox_str = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
    all_hotspots = []
    
    curr_dt = start_dt
    while curr_dt <= end_dt:
        chunk_end = min(curr_dt + timedelta(days=9), end_dt)
        duration_days = (chunk_end - curr_dt).days + 1
        
        # Determine source
        days_ago = (now - curr_dt).days
        source = "VIIRS_SNPP_SP" if days_ago > 14 else "VIIRS_SNPP_NRT"
        
        date_str = curr_dt.strftime("%Y-%m-%d")
        
        chunk_hotspots = _fetch_firms_chunk(map_key, source, bbox_str, duration_days, date_str)
        all_hotspots.extend(chunk_hotspots)
        
        curr_dt = chunk_end + timedelta(days=1)
        
    fire_context_per_region = {}
    
    for region in regions:
        # Fallback to centroid_xy if geo_centroid is missing?
        # FIRMS provides lat/lon, so we need geo_centroid.
        if not region.geo_centroid and not region.geo_bbox:
            continue
            
        r_lon, r_lat = region.geo_centroid if region.geo_centroid else (
            (region.geo_bbox[0] + region.geo_bbox[2])/2, 
            (region.geo_bbox[1] + region.geo_bbox[3])/2
        )
        
        count = 0
        min_dist = float('inf')
        dates = set()
        
        for hs in all_hotspots:
            hs_lat = float(hs['latitude'])
            hs_lon = float(hs['longitude'])
            
            dist = _haversine_distance(r_lon, r_lat, hs_lon, hs_lat)
            if dist < min_dist:
                min_dist = dist
                
            if dist <= 2.0: # threshold for nearby (2km)
                count += 1
                dates.add(hs['acq_date'])
                
        fire_context_per_region[region.region_id] = {
            "nearby": count > 0,
            "count": count,
            "nearest_km": round(min_dist, 3) if min_dist != float('inf') else None,
            "dates": sorted(list(dates))
        }
        
    return fire_context_per_region
