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
from typing import List, Optional, Tuple
import numpy as np
import scipy.ndimage as ndimage

from src.api.schemas import ChangedRegion


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
    bbox: List[float],
    image_shape: Tuple[int, int],
) -> Tuple[float, float]:
    """
    Convert (row, col) pixel coordinate to (lon, lat) geographic coordinate.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    h, w = image_shape

    lon = min_lon + (col / max(w, 1)) * (max_lon - min_lon)
    lat = max_lat - (row / max(h, 1)) * (max_lat - min_lat)  # Row 0 is at top (max_lat)
    return round(lon, 6), round(lat, 6)


def extract_changed_regions(
    binary_mask: np.ndarray,
    prob_map: np.ndarray,
    min_region_area_px: int = 10,
    bbox: Optional[List[float]] = None,
) -> Tuple[List[ChangedRegion], float]:
    """
    Extract discrete change regions using connected components analysis.

    Returns:
        tuple (regions_list, total_changed_area_sq_km)
    """
    labeled_array, num_features = ndimage.label(binary_mask > 0)
    h, w = binary_mask.shape

    pixel_area_km2 = None
    if bbox is not None and len(bbox) == 4:
        pixel_area_km2 = compute_approx_pixel_area_km2(bbox, (h, w))

    regions: List[ChangedRegion] = []
    region_slices = ndimage.find_objects(labeled_array)

    total_changed_px = int(np.sum(binary_mask > 0))
    total_changed_km2 = (
        round(total_changed_px * pixel_area_km2, 4)
        if pixel_area_km2 is not None
        else None
    )

    MERGE_GAP_PX = 10

    raw_regions = []
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

        raw_regions.append({
            "min_row": min_row,
            "max_row": max_row,
            "min_col": min_col,
            "max_col": max_col,
            "area_px": area_px,
            "sum_c": global_centroid_c * area_px,
            "sum_r": global_centroid_r * area_px,
            "sum_prob": mean_prob * area_px,
        })

    # Transitive Merge
    parent = list(range(len(raw_regions)))

    def find(i: int) -> int:
        if parent[i] == i:
            return i
        parent[i] = find(parent[i])
        return parent[i]

    def union(i: int, j: int):
        root_i = find(i)
        root_j = find(j)
        if root_i != root_j:
            parent[root_i] = root_j

    for i in range(len(raw_regions)):
        for j in range(i + 1, len(raw_regions)):
            b1 = raw_regions[i]
            b2 = raw_regions[j]
            vert_gap = max(0, max(b1["min_row"], b2["min_row"]) - min(b1["max_row"], b2["max_row"]))
            horiz_gap = max(0, max(b1["min_col"], b2["min_col"]) - min(b1["max_col"], b2["max_col"]))
            if max(vert_gap, horiz_gap) <= MERGE_GAP_PX:
                union(i, j)

    merged_groups = {}
    for i in range(len(raw_regions)):
        root = find(i)
        if root not in merged_groups:
            merged_groups[root] = []
        merged_groups[root].append(raw_regions[i])

    regions: List[ChangedRegion] = []
    region_counter = 1

    for root, group in merged_groups.items():
        area_px = sum(g["area_px"] for g in group)
        min_row = min(g["min_row"] for g in group)
        max_row = max(g["max_row"] for g in group)
        min_col = min(g["min_col"] for g in group)
        max_col = max(g["max_col"] for g in group)
        global_centroid_c = sum(g["sum_c"] for g in group) / area_px
        global_centroid_r = sum(g["sum_r"] for g in group) / area_px
        mean_prob = sum(g["sum_prob"] for g in group) / area_px

        # Geo-referencing if bbox is available
        geo_bbox = None
        geo_centroid = None
        if bbox is not None:
            c1_lon, c1_lat = pixel_to_geo_coords(max_row, min_col, bbox, (h, w)) # SW
            c2_lon, c2_lat = pixel_to_geo_coords(min_row, max_col, bbox, (h, w)) # NE
            geo_bbox = (c1_lon, c1_lat, c2_lon, c2_lat)
            c_lon, c_lat = pixel_to_geo_coords(global_centroid_r, global_centroid_c, bbox, (h, w))
            geo_centroid = (c_lon, c_lat)

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
        elif area_px >= 300 or mean_prob >= 0.85:
            severity = "Critical"
            label = "Significant Structural / Ground Disturbance"
        elif area_px >= 100 or mean_prob >= 0.70:
            severity = "High"
            label = "Definite Surface / Backscatter Anomaly"
        elif area_px >= 30:
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
                centroid_xy=(round(global_centroid_c, 2), round(global_centroid_r, 2)),
                bbox_xy=(min_row, min_col, max_row, max_col),
                geo_bbox=geo_bbox,
                geo_centroid=geo_centroid,
                mean_change_prob=round(mean_prob, 4),
                severity=severity,
                label=label,
            )
        )
        region_counter += 1

    # Sort regions by area descending
    regions.sort(key=lambda r: r.area_px, reverse=True)

    return regions, total_changed_km2
