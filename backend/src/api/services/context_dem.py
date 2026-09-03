import logging
import numpy as np
from typing import Dict, List, Optional
from src.api.schemas import ChangedRegion

logger = logging.getLogger(__name__)

def process_dem_tile(dem_bytes: bytes, regions: List[ChangedRegion]) -> Dict[int, dict]:
    """
    Process Copernicus DEM bytes and extract terrain metrics per region.
    """
    try:
        import rasterio
        from rasterio.io import MemoryFile
    except ImportError:
        logger.error("rasterio is required for DEM decoding.")
        return {r.region_id: _fallback_dem() for r in regions}

    try:
        with MemoryFile(dem_bytes) as memfile:
            with memfile.open() as dataset:
                dem_arr = dataset.read(1) # shape (H, W)
                
        h, w = dem_arr.shape
        
        # Calculate approximate slope using gradient
        # Note: This is an approximation since dx/dy are in pixels, not meters,
        # but it serves as a heuristic for steep vs flat terrain.
        dy, dx = np.gradient(dem_arr)
        # Normalize gradient to approximate 10m/pixel (Sentinel-1 high res)
        slope = np.arctan(np.sqrt((dx/10.0)**2 + (dy/10.0)**2)) * (180.0 / np.pi)
        
        dem_context_per_region = {}
        for region in regions:
            min_row, min_col, max_row, max_col = region.bbox_xy
            
            # Ensure bounds are valid
            min_row, max_row = max(0, min_row), min(h, max_row)
            min_col, max_col = max(0, min_col), min(w, max_col)
            
            if min_row >= max_row or min_col >= max_col:
                dem_context_per_region[region.region_id] = _fallback_dem()
                continue
                
            region_elevation = np.mean(dem_arr[min_row:max_row, min_col:max_col])
            region_slope = np.mean(slope[min_row:max_row, min_col:max_col])
            flat = bool(region_slope < 5.0)
            
            layover_shadow_overlap_pct = 0.0
            if region_slope > 20.0:
                layover_shadow_overlap_pct = 50.0  # Heuristic for steep terrain
            
            dem_context_per_region[region.region_id] = {
                "mean_elevation_m": float(region_elevation),
                "mean_slope_deg": float(region_slope),
                "flat": flat,
                "layover_shadow_overlap_pct": layover_shadow_overlap_pct
            }
        return dem_context_per_region
    except Exception as e:
        logger.error(f"Failed to process DEM tile: {e}")
        return {r.region_id: _fallback_dem() for r in regions}

def _fallback_dem() -> dict:
    return {
        "mean_elevation_m": 0.0,
        "mean_slope_deg": 0.0,
        "flat": True,
        "layover_shadow_overlap_pct": 0.0
    }
