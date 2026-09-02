import logging
import requests
import time
import json
import functools
from typing import List, Dict, Optional, Tuple
from shapely.geometry import Point, LineString, Polygon, shape, mapping
from shapely.ops import transform
import pyproj

from src.api.schemas import ChangedRegion
from src.api.services.change_analyzer import _get_utm_proj

logger = logging.getLogger(__name__)

PRIMARY_ENDPOINT = "https://overpass-api.de/api/interpreter"
FALLBACK_ENDPOINTS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
]
USER_AGENT = "GeoPulse-Mission-Platform/1.0 (Contact: admin@geopulse.local)"

def _fetch_with_retry(query: str, endpoint: str) -> Optional[dict]:
    headers = {"User-Agent": USER_AGENT}
    max_retries = 3
    base_wait = 2.0
    
    for attempt in range(max_retries):
        try:
            resp = requests.post(endpoint, data={"data": query}, headers=headers, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                if attempt == max_retries - 1:
                    break
                wait_time = base_wait * (2 ** attempt)
                logger.warning(f"Overpass 429 Too Many Requests. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                logger.warning(f"Overpass API returned {resp.status_code}: {resp.text}")
                break
        except requests.exceptions.RequestException as e:
            logger.warning(f"Overpass request failed: {e}")
            break
            
    return None

@functools.lru_cache(maxsize=32)
def _fetch_overpass_cached(bbox_rounded: Tuple[float, float, float, float]) -> Optional[dict]:
    min_lon, min_lat, max_lon, max_lat = bbox_rounded
    
    query = f"""
    [out:json][timeout:25];
    (
      way["highway"]({min_lat},{min_lon},{max_lat},{max_lon});
      way["building"]({min_lat},{min_lon},{max_lat},{max_lon});
      node["building"]({min_lat},{min_lon},{max_lat},{max_lon});
      way["landuse"="industrial"]({min_lat},{min_lon},{max_lat},{max_lon});
      way["water"]({min_lat},{min_lon},{max_lat},{max_lon});
      relation["water"]({min_lat},{min_lon},{max_lat},{max_lon});
      way["natural"="water"]({min_lat},{min_lon},{max_lat},{max_lon});
      relation["natural"="water"]({min_lat},{min_lon},{max_lat},{max_lon});
    );
    out body geom;
    """
    
    endpoints = [PRIMARY_ENDPOINT] + FALLBACK_ENDPOINTS
    for endpoint in endpoints:
        result = _fetch_with_retry(query, endpoint)
        if result is not None:
            return result
            
    return None

def _parse_geometries(elements: List[dict]) -> dict:
    features = {
        "roads": [],
        "buildings": [],
        "industrial": [],
        "water": []
    }
    
    for el in elements:
        geom = None
        if el["type"] == "node":
            geom = Point(el["lon"], el["lat"])
        elif el["type"] == "way":
            if "geometry" in el:
                coords = [(pt["lon"], pt["lat"]) for pt in el["geometry"]]
                if len(coords) >= 4 and coords[0] == coords[-1]:
                    geom = Polygon(coords)
                elif len(coords) >= 2:
                    geom = LineString(coords)
        elif el["type"] == "relation":
            if "bounds" in el:
                b = el["bounds"]
                geom = Polygon([
                    (b["minlon"], b["minlat"]),
                    (b["maxlon"], b["minlat"]),
                    (b["maxlon"], b["maxlat"]),
                    (b["minlon"], b["maxlat"]),
                    (b["minlon"], b["minlat"])
                ])
                
        if not geom:
            continue
            
        tags = el.get("tags", {})
        if "highway" in tags:
            features["roads"].append(geom)
        if "building" in tags:
            features["buildings"].append(geom)
        if tags.get("landuse") == "industrial":
            features["industrial"].append(geom)
        if "water" in tags or tags.get("natural") == "water":
            features["water"].append(geom)
            
    return features

def get_osm_context(regions: List[ChangedRegion], aoi_bbox: List[float]) -> Dict[int, dict]:
    if not regions or not aoi_bbox:
        return {}
        
    # Buffer AOI by roughly 2000m (0.02 degrees)
    buffer_deg = 0.02
    buffered_bbox = (
        round(aoi_bbox[0] - buffer_deg, 3),
        round(aoi_bbox[1] - buffer_deg, 3),
        round(aoi_bbox[2] + buffer_deg, 3),
        round(aoi_bbox[3] + buffer_deg, 3)
    )
    
    osm_data = _fetch_overpass_cached(buffered_bbox)
    if not osm_data or "elements" not in osm_data:
        return {}
        
    features_wgs84 = _parse_geometries(osm_data["elements"])
    
    context_per_region = {}
    
    for region in regions:
        if not region.geo_centroid:
            continue
            
        c_lon, c_lat = region.geo_centroid
        centroid_wgs84 = Point(c_lon, c_lat)
        
        wgs84_proj = pyproj.Proj("EPSG:4326")
        utm_proj = _get_utm_proj(c_lon, c_lat)
        project_to_utm = functools.partial(pyproj.transform, wgs84_proj, utm_proj)
        
        centroid_utm = transform(project_to_utm, centroid_wgs84)
        
        # Determine nearest road
        nearest_road_m = None
        for road_geom in features_wgs84["roads"]:
            road_utm = transform(project_to_utm, road_geom)
            dist = centroid_utm.distance(road_utm)
            if nearest_road_m is None or dist < nearest_road_m:
                nearest_road_m = dist
                
        # Determine nearest water
        nearest_water_m = None
        for water_geom in features_wgs84["water"]:
            water_utm = transform(project_to_utm, water_geom)
            dist = centroid_utm.distance(water_utm)
            if nearest_water_m is None or dist < nearest_water_m:
                nearest_water_m = dist
                
        # Count buildings within 500m
        buildings_within_500m = 0
        building_buffer = centroid_utm.buffer(500)
        for bldg_geom in features_wgs84["buildings"]:
            bldg_utm = transform(project_to_utm, bldg_geom)
            if building_buffer.intersects(bldg_utm):
                buildings_within_500m += 1
                
        # Check industrial presence
        industrial = False
        industrial_buffer = centroid_utm.buffer(100) # 100m tolerance
        for ind_geom in features_wgs84["industrial"]:
            ind_utm = transform(project_to_utm, ind_geom)
            if industrial_buffer.intersects(ind_utm):
                industrial = True
                break
                
        context_per_region[region.region_id] = {
            "nearest_road_m": round(nearest_road_m, 2) if nearest_road_m is not None else None,
            "buildings_within_500m": buildings_within_500m,
            "industrial": industrial,
            "nearest_water_m": round(nearest_water_m, 2) if nearest_water_m is not None else None
        }
        
    return context_per_region
