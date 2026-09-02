import logging
import os
import functools
import numpy as np
from typing import Dict, List, Tuple
from src.api.schemas import ChangedRegion

logger = logging.getLogger(__name__)

WORLDCOVER_CLASS_CODES = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / sparse vegetation",
    70: "Snow and ice",
    80: "Permanent water bodies",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen"
}

@functools.lru_cache(maxsize=128)
def _fetch_worldcover_window(min_lon: float, min_lat: float, max_lon: float, max_lat: float):
    """
    Fetch the ESA WorldCover 10m COG window.
    Deterministically cached for repeated calls.
    """
    try:
        import rasterio
        from rasterio.windows import from_bounds
        
        cog_url = os.environ.get(
            "WORLDCOVER_COG_URL",
            "s3://esa-worldcover/v200/2021/ESA_WorldCover_10m_2021_v200_Map_AWS.vrt"
        )
        
        with rasterio.open(cog_url) as src:
            window = from_bounds(min_lon, min_lat, max_lon, max_lat, src.transform)
            # Ensure window is valid
            if window.width <= 0 or window.height <= 0:
                return None
            
            # Use boundless to avoid errors at edge of raster
            arr = src.read(1, window=window, boundless=True, fill_value=0)
            return arr
    except Exception as e:
        logger.error(f"WorldCover fetch failed: {e}")
        return None

def get_landcover_context(regions: List[ChangedRegion]) -> Dict[int, dict]:
    """
    For each region, uses geo_bbox to fetch landcover and calculate histogram.
    """
    landcover_context_per_region = {}
    
    for region in regions:
        if not region.geo_bbox:
            continue
            
        min_lon, min_lat, max_lon, max_lat = region.geo_bbox
        # Slight buffer to ensure we get pixels even for tiny regions
        arr = _fetch_worldcover_window(
            min_lon - 0.0001, min_lat - 0.0001, 
            max_lon + 0.0001, max_lat + 0.0001
        )
        
        if arr is None or arr.size == 0:
            continue
            
        # Calculate histogram
        unique, counts = np.unique(arr, return_counts=True)
        total_pixels = arr.size
        
        class_histogram = {}
        dominant_code = 0
        max_count = -1
        
        for val, count in zip(unique, counts):
            if val == 0: # No data
                continue
            code = int(val)
            pct = (count / total_pixels) * 100.0
            
            # Map code to string, fallback to "Unknown"
            name = WORLDCOVER_CLASS_CODES.get(code, f"Unknown ({code})")
            class_histogram[name] = float(pct)
            
            if count > max_count:
                max_count = count
                dominant_code = code
                
        if dominant_code > 0:
            dominant_name = WORLDCOVER_CLASS_CODES.get(dominant_code, f"Unknown ({dominant_code})")
            
            is_cropland_dominant = bool(dominant_code == 40)
            is_tree_consistent = bool(dominant_code in [10, 20, 95])
            is_sparse_built_consistent = bool(dominant_code in [50, 60])
            
            landcover_context_per_region[region.region_id] = {
                "dominant_class": dominant_name,
                "dominant_class_code": dominant_code,
                "class_histogram": class_histogram,
                "is_cropland_dominant": is_cropland_dominant,
                "is_tree_consistent": is_tree_consistent,
                "is_sparse_built_consistent": is_sparse_built_consistent
            }

    return landcover_context_per_region
