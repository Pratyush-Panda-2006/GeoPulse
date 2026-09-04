"""
src/api/services/change_analyzer.py
===================================
Intelligence & post-processing service for SAR Change Detection:
- Connected component clustering & region extraction
- Geographic footprint & area estimation
- Calibrated priority scoring & uncertainty flagging
"""

from __future__ import annotations

import math
from typing import Any, List, Optional, Tuple
import numpy as np
import scipy.ndimage as ndimage
import pyproj
from shapely.geometry import shape, MultiPolygon
from shapely.ops import transform as shapely_transform
from functools import partial

from src.api.schemas import ChangedRegion


def _get_utm_proj(lon: float, lat: float) -> pyproj.Proj:
    """Get the UTM projection for a given lon/lat."""
    zone = int(math.floor((lon + 180) / 6.0) + 1)
    # EPSG:326xx for North, EPSG:327xx for South
    epsg_code = 32600 + zone if lat >= 0 else 32700 + zone
    return pyproj.Proj(f"EPSG:{epsg_code}")



def compute_approx_pixel_area_km2(bbox: List[float], image_shape: Tuple[int, int]) -> float:
    """
    Approximate square kilometers represented by 1 pixel given WGS84 BBox [min_lon, min_lat, max_lon, max_lat]
    and image dimensions (H, W).
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    h, w = image_shape

    # Approximate 1 degree latitude = 111.0 km
    lat_center = (min_lat + max_lat) / 2.0
    lat_span_km = abs(max_lat - min_lat) * 111.0
    lon_span_km = abs(max_lon - min_lon) * 111.0 * math.cos(math.radians(lat_center))

    total_area_km2 = lat_span_km * lon_span_km
    total_pixels = h * w
    return total_area_km2 / max(total_pixels, 1)


def pixel_to_geo_coords(
    row: float,
    col: float,
    bbox: Optional[List[float]],
    image_shape: Tuple[int, int],
    transform: Any = None,
    crs: Any = None,
) -> Tuple[float, float]:
    """
    Convert (row, col) pixel coordinate to (lon, lat) geographic coordinate.
    If a real rasterio Affine transform is provided, it uses exact reprojection.
    If the source CRS is not EPSG:4326, it reprojects to WGS84 lon/lat.
    Otherwise, it linearly interpolates within the bbox (legacy fallback).
    """
    if transform is not None and crs is not None:
        try:
            import rasterio
            from rasterio.warp import transform as warp_transform
            from rasterio.crs import CRS
            
            x, y = rasterio.transform.xy(transform, row, col, offset="center")
            
            wgs84 = CRS.from_epsg(4326)
            if crs != wgs84:
                # rasterio.warp.transform returns (xs, ys)
                lons, lats = warp_transform(crs, wgs84, [x], [y])
                lon, lat = lons[0], lats[0]
            else:
                lon, lat = x, y
                
            return round(lon, 6), round(lat, 6)
        except Exception:
            pass

    # Legacy bbox linear interpolation fallback
    if bbox is not None and len(bbox) == 4:
        min_lon, min_lat, max_lon, max_lat = bbox
        h, w = image_shape
        lon = min_lon + (col / max(w, 1)) * (max_lon - min_lon)
        lat = max_lat - (row / max(h, 1)) * (max_lat - min_lat)  # Row 0 is at top (max_lat)
        return round(lon, 6), round(lat, 6)
        
    return 0.0, 0.0


def extract_changed_regions(
    binary_mask: np.ndarray,
    prob_map: np.ndarray,
    min_region_area_px: int = 10,
    bbox: Optional[List[float]] = None,
    transform: Any = None,
    crs: Any = None,
) -> Tuple[List[ChangedRegion], float]:
    """
    Extract discrete change regions using connected components analysis.

    Returns:
        tuple (regions_list, total_changed_area_sq_km)
    """
    # 1. Morphological Noise Removal
    # Opening removes small false positives (salt noise)
    cleaned_mask = ndimage.binary_opening(binary_mask > 0, structure=np.ones((3, 3)))
    # Closing bridges small gaps and completes structures (pepper noise/broken edges)
    cleaned_mask = ndimage.binary_closing(cleaned_mask, structure=np.ones((5, 5)))
    
    labeled_array, num_features = ndimage.label(cleaned_mask)
    h, w = binary_mask.shape

    pixel_area_km2 = None
    if bbox is not None and len(bbox) == 4:
        pixel_area_km2 = compute_approx_pixel_area_km2(bbox, (h, w))

    regions: List[ChangedRegion] = []
    region_slices = ndimage.find_objects(labeled_array)

    total_changed_px = int(np.sum(cleaned_mask))
    total_changed_km2 = (
        round(total_changed_px * pixel_area_km2, 4)
        if pixel_area_km2 is not None
        else None
    )

    wgs84 = pyproj.Proj("EPSG:4326")

    # For accurate geometry, we'll need rasterio.features
    try:
        from rasterio import features
        has_features = True
    except ImportError:
        has_features = False

    region_counter = 1
    for idx, slc in enumerate(region_slices, start=1):
        if slc is None:
            continue

        region_mask = (labeled_array[slc] == idx)
        area_px = int(np.sum(region_mask))

        if area_px < min_region_area_px:
            continue

        # Bounding box in pixel coordinates (min_row, min_col, max_row, max_col)
        min_row = int(slc[0].start)
        max_row = int(slc[0].stop)
        min_col = int(slc[1].start)
        max_col = int(slc[1].stop)

        # Centroid
        centroid_row, centroid_col = ndimage.center_of_mass(region_mask)
        global_centroid_r = min_row + centroid_row
        global_centroid_c = min_col + centroid_col

        # Mean change probability within this region
        region_probs = prob_map[slc][region_mask]
        mean_prob = float(np.mean(region_probs)) if len(region_probs) > 0 else 0.5

        # Geo-referencing if bbox or transform is available
        geo_bbox = None
        geo_centroid = None
        area_km2 = None
        
        if bbox is not None or (transform is not None and crs is not None):
            c1_lon, c1_lat = pixel_to_geo_coords(max_row, min_col, bbox, (h, w), transform, crs) # SW
            c2_lon, c2_lat = pixel_to_geo_coords(min_row, max_col, bbox, (h, w), transform, crs) # NE
            geo_bbox = (c1_lon, c1_lat, c2_lon, c2_lat)
            c_lon, c_lat = pixel_to_geo_coords(global_centroid_r, global_centroid_c, bbox, (h, w), transform, crs)
            geo_centroid = (c_lon, c_lat)
            
            # Extract precise polygon geometry and equal-area km2
            if has_features and transform is not None:
                # We extract the mask for this specific merged group
                group_mask = np.zeros_like(cleaned_mask, dtype=np.uint8)
                group_mask[min_row:max_row, min_col:max_col] = region_mask.astype(np.uint8)
                
                # Full array approach (safer for transform)
                shapes = list(features.shapes(group_mask, transform=transform))
                polygons = []
                for geom, val in shapes:
                    if val == 1:
                        polygons.append(shape(geom))
                
                if polygons:
                    geom = MultiPolygon(polygons) if len(polygons) > 1 else polygons[0]
                    # Transform to WGS84 to ensure lat/lon for UTM calculation
                    try:
                        import rasterio.warp
                    except ImportError:
                        pass

                    # Transform to UTM for equal-area
                    utm_proj = _get_utm_proj(c_lon, c_lat)
                    project = partial(pyproj.transform, wgs84, utm_proj)
                    geom_utm = shapely_transform(project, geom)
                    area_km2 = geom_utm.area / 1e6
            
            # Fallback if area_km2 wasn't computed exactly
            if area_km2 is None and pixel_area_km2 is not None:
                area_km2 = round(area_px * pixel_area_km2, 6)

        approx_area_km2 = (
            round(area_px * pixel_area_km2, 6)
            if pixel_area_km2 is not None
            else None
        )

        # Classify Severity & Uncertainty
        # Check if borderline uncertain
        if 0.45 <= mean_prob <= 0.55:
            severity = "Uncertain"
            label = "Borderline / Low SNR Surface Change"
        elif area_px >= 200:
            severity = "High"
            label = "Significant Structural / Ground Disturbance"
        elif area_px >= 130:
            severity = "Medium"
            label = "Moderate Change Cluster"
        else:
            severity = "Low"
            label = "Localized Minor Surface Change"

        regions.append(
            ChangedRegion(
                region_id=region_counter,
                area_px=area_px,
                approx_area_sq_km=approx_area_km2,
                area_km2=round(area_km2, 4) if area_km2 is not None else approx_area_km2,
                centroid_xy=(round(global_centroid_c, 2), round(global_centroid_r, 2)),
                bbox_xy=(min_row, min_col, max_row, max_col),
                geo_bbox=geo_bbox,
                geo_centroid=geo_centroid,
                mean_change_prob=round(mean_prob, 4),
                severity=severity,
                label=label,
                evidence=None, # Will be populated by evidence engine
            )
        )
        region_counter += 1

    # Sort regions by area descending
    regions.sort(key=lambda r: r.area_px, reverse=True)
    
    total_area_km2 = sum(r.area_km2 for r in regions) if any(r.area_km2 for r in regions) else total_changed_km2

    return regions, total_area_km2

