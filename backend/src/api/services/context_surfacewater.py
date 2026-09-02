import logging
import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.features import shapes
from shapely.geometry import shape, MultiPolygon
from shapely.ops import transform
from functools import partial
import pyproj
import functools
from skimage.filters import threshold_otsu
import scipy.ndimage
from typing import List, Dict, Optional, Tuple

from src.api.schemas import ChangedRegion
from src.api.services.change_analyzer import _get_utm_proj

logger = logging.getLogger(__name__)

JRC_WATER_COG_URL = "https://storage.googleapis.com/global-surface-water/downloads2021/occurrence/occurrence_90W_0N.tif"
PERMANENT_WATER_THRESHOLD = 80

@functools.lru_cache(maxsize=32)
def _fetch_jrc_water_window(bbox: tuple) -> Tuple[Optional[np.ndarray], Optional[rasterio.Affine]]:
    try:
        with rasterio.open(JRC_WATER_COG_URL) as src:
            min_lon, min_lat, max_lon, max_lat = bbox
            window = rasterio.windows.from_bounds(min_lon, min_lat, max_lon, max_lat, transform=src.transform)
            data = src.read(1, window=window)
            return data, src.window_transform(window)
    except Exception as e:
        logger.warning(f"Failed to fetch JRC water occurrence: {e}")
        return None, None

def _calculate_equal_area_km2(mask: np.ndarray, transform_wgs84: rasterio.Affine) -> float:
    if mask.sum() == 0:
        return 0.0
        
    mask_uint8 = mask.astype(np.uint8)
    polys = []
    for geom, val in shapes(mask_uint8, transform=transform_wgs84):
        if val == 1:
            polys.append(shape(geom))
            
    if not polys:
        return 0.0
        
    geom = MultiPolygon(polys) if len(polys) > 1 else polys[0]
    
    # We can use the centroid of the multipolygon for the UTM projection
    c_lon, c_lat = geom.centroid.x, geom.centroid.y
    wgs84 = pyproj.Proj("EPSG:4326")
    utm_proj = _get_utm_proj(c_lon, c_lat)
    project = partial(pyproj.transform, wgs84, utm_proj)
    
    geom_utm = transform(project, geom)
    return geom_utm.area / 1e6

def get_surface_water_context(
    regions: List[ChangedRegion], 
    t2_array: np.ndarray, 
    bbox: List[float], 
    mission_config: dict
) -> Dict[int, dict]:
    if t2_array is None:
        return {}
        
    if t2_array.ndim == 3:
        vv_array = t2_array[0]
    else:
        vv_array = t2_array

    jrc_data, jrc_transform = _fetch_jrc_water_window(tuple(bbox))
    
    context_per_region = {}
    
    for region in regions:
        if not region.bbox_xy or not region.geo_bbox:
            continue
            
        xmin, ymin, xmax, ymax = region.bbox_xy
        
        region_vv = vv_array[ymin:ymax, xmin:xmax]
        
        valid_vv = region_vv[(region_vv > 0) & (~np.isnan(region_vv))]
        
        if valid_vv.size > 0:
            try:
                # Otsu requires at least two distinct values
                if np.ptp(valid_vv) == 0:
                    threshold = 0.05
                else:
                    threshold = threshold_otsu(valid_vv)
            except Exception:
                threshold = 0.05
        else:
            threshold = 0.05
            
        water_mask = (region_vv < threshold) & (region_vv > 0)
        
        permanent_water_mask = np.zeros_like(water_mask)
        if jrc_data is not None:
            try:
                zoom_y = region_vv.shape[0] / jrc_data.shape[0]
                zoom_x = region_vv.shape[1] / jrc_data.shape[1]
                jrc_resized = scipy.ndimage.zoom(jrc_data, (zoom_y, zoom_x), order=0) # nearest neighbor
                permanent_water_mask = jrc_resized > PERMANENT_WATER_THRESHOLD
            except Exception as e:
                logger.warning(f"Failed to align JRC data: {e}")
                
        new_water_mask = water_mask & (~permanent_water_mask)
        perm_water_mask = water_mask & permanent_water_mask
        
        min_lon, min_lat, max_lon, max_lat = region.geo_bbox
        region_transform = rasterio.transform.from_bounds(
            min_lon, min_lat, max_lon, max_lat, 
            region_vv.shape[1], region_vv.shape[0]
        )
        
        new_water_km2 = _calculate_equal_area_km2(new_water_mask, region_transform)
        permanent_water_km2 = _calculate_equal_area_km2(perm_water_mask, region_transform)
            
        context_per_region[region.region_id] = {
            "new_water_km2": round(new_water_km2, 4),
            "permanent_water_km2": round(permanent_water_km2, 4)
        }
        
    return context_per_region
