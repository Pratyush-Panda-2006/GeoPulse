import datetime as dt
import logging
import yaml
from pathlib import Path
from src.api.schemas import AnalyzeRequest, AnalysisResult, AnalysisSummary, TimeSeriesAcquisition, LayerConfig
from src.data_ingestion.sar_timeseries import fetch_sar_timeseries
from src.data_ingestion.sentinel_client import CDSEAuthManager, SentinelHubClient
from src.api.services.inference_service import run_change_detection
from src.api.services.context_dem import process_dem_tile
from src.api.services.evidence_engine import synthesize_evidence
from src.api.services.context_weather import get_weather_context, detect_event_date
import hashlib
import json
from shapely.geometry import shape

logger = logging.getLogger(__name__)

def load_missions():
    missions_path = Path(__file__).parent.parent.parent.parent / "missions.yaml"
    if missions_path.exists():
        with open(missions_path, "r") as f:
            return yaml.safe_load(f).get("missions", {})
    return {}

def run_analysis(req: AnalyzeRequest) -> AnalysisResult:
    # 1. Parse AOI
    if "type" in req.aoi and req.aoi["type"] in ["Polygon", "MultiPolygon"]:
        geom = shape(req.aoi)
        bounds = geom.bounds
        bbox = [bounds[0], bounds[1], bounds[2], bounds[3]]
    else:
        bbox = req.aoi.get("bbox")
        if not bbox:
            raise ValueError("Invalid AOI: must be GeoJSON Polygon or provide bbox array")

    # 2. Setup CDSE Auth
    auth = CDSEAuthManager()
    
    # Check cache mode (P0 simple cache check based on request parameters)
    # We will compute a hash of the request to check cache
    # But since P0 says "cache mode (return 404/miss if not present; never fall back to live inference)"
    # We will just raise if it's cached mode and not found. 
    # For now, we only implement the live path, and mock cache misses.
    if req.mode == "cached":
        raise ValueError("Cache miss: This analysis has not been precomputed.")

    # 3. Discovery and Fetch (Oldest/Latest)
    event_date_str = req.event_date
    if not event_date_str and req.mission in ["disaster", "flood", "landslide", "cyclone"]:
        logger.info(f"Detecting event date for mission: {req.mission}")
        event_date_str = detect_event_date(bbox, req.period["start"], req.period["end"])

    event_date = dt.date.fromisoformat(event_date_str) if event_date_str else None
    
    selection, t1_dict, t2_dict, all_metadata = fetch_sar_timeseries(
        bbox=bbox,
        date_range=(req.period["start"], req.period["end"]),
        output_resolution=req.resolution,
        max_scenes=20,  # Ensure we discover all within a reasonable limit
        auth=auth,
        strategy="progressive",
        event_date=event_date
    )

    t1_meta = t1_dict["meta"]
    t2_meta = t2_dict["meta"]

    # 4. Inference
    inference_result = run_change_detection(
        t1_np=t1_dict["array"],
        t2_np=t2_dict["array"],
        model_name=req.model_name,
        threshold=req.threshold,
        min_region_area_px=req.min_region_area_px,
        bbox=bbox,
        transform=None,  # We'll rely on bbox for approximate coords if transform unavailable
        crs=None
    )

    # 5. Terrain Context (DEM)
    missions = load_missions()
    mission_config = missions.get(req.mission, {})
    
    dem_context_per_region = {}
    if "dem" in mission_config.get("layers", []):
        try:
            client = SentinelHubClient(auth)
            dem_bytes = client.fetch_dem_tile(bbox=bbox, output_resolution=req.resolution)
            dem_context_per_region = process_dem_tile(dem_bytes, inference_result.regions)
        except Exception as e:
            logger.warning(f"Failed to fetch DEM context: {e}")

    # 5.1 Weather Context
    weather_context = None
    if "weather" in mission_config.get("layers", []):
        try:
            weather_context = get_weather_context(
                bbox=bbox,
                start_date=req.period["start"],
                end_date=req.period["end"],
                event_date=event_date_str
            )
        except Exception as e:
            logger.warning(f"Failed to fetch Weather context: {e}")

    # 5.2 Landcover Context
    landcover_context_per_region = {}
    if "landcover" in mission_config.get("layers", []):
        try:
            from src.api.services.context_landcover import get_landcover_context
            landcover_context_per_region = get_landcover_context(inference_result.regions)
        except Exception as e:
            logger.warning(f"Failed to fetch Landcover context: {e}")

    # 5.3 Fire Context
    fire_context_per_region = {}
    if "fire" in mission_config.get("layers", []):
        try:
            from src.api.services.context_fire import get_fire_context
            fire_context_per_region = get_fire_context(
                inference_result.regions, 
                bbox, 
                req.period["start"], 
                req.period["end"]
            )
        except Exception as e:
            logger.warning(f"Failed to fetch Fire context: {e}")

    # 5.4 Surface Water Context
    surface_water_context_per_region = {}
    if "surface_water" in mission_config.get("layers", []) or req.mission == "flood":
        try:
            from src.api.services.context_surfacewater import get_surface_water_context
            surface_water_context_per_region = get_surface_water_context(
                regions=inference_result.regions,
                t2_array=t2_dict["array"],
                bbox=bbox,
                mission_config=mission_config
            )
        except Exception as e:
            logger.warning(f"Failed to fetch Surface Water context: {e}")

    # 5.5 OSM Context
    osm_context_per_region = {}
    if "osm" in mission_config.get("layers", []) or req.mission in ["deforestation", "mining", "general"]:
        try:
            from src.api.services.context_osm import get_osm_context
            osm_context_per_region = get_osm_context(inference_result.regions, bbox)
        except Exception as e:
            logger.warning(f"Failed to fetch OSM context: {e}")

    # 6. Evidence Engine Synthesis & GeoJSON construction
    features = []
    for region in inference_result.regions:
        dem_ctx = dem_context_per_region.get(region.region_id)
        landcover_ctx = landcover_context_per_region.get(region.region_id)
        fire_ctx = fire_context_per_region.get(region.region_id)
        surface_water_ctx = surface_water_context_per_region.get(region.region_id)
        osm_ctx = osm_context_per_region.get(region.region_id)
        
        evidence = synthesize_evidence(
            region, 
            dem_context=dem_ctx, 
            landcover_context=landcover_ctx,
            fire_context=fire_ctx,
            surface_water_context=surface_water_ctx,
            osm_context=osm_ctx,
            mission_config=mission_config
        )
        region.evidence = evidence
        
        # Build GeoJSON feature
        # Fallback to bbox if exact geometry is missing
        if region.geo_bbox:
            min_lon, min_lat, max_lon, max_lat = region.geo_bbox
            poly = {
                "type": "Polygon",
                "coordinates": [[
                    [min_lon, min_lat],
                    [max_lon, min_lat],
                    [max_lon, max_lat],
                    [min_lon, max_lat],
                    [min_lon, min_lat]
                ]]
            }
        else:
            poly = None
            
        if poly:
            features.append({
                "type": "Feature",
                "geometry": poly,
                "properties": region.dict(exclude={"bbox_xy", "centroid_xy", "geo_bbox", "geo_centroid"})
            })

    # Phase N4 & N5: Nemotron Multimodal Classification (with context)
    from src.api.services.vision_pipeline import orchestrate_vision_classification
    
    nemotron_interpretations = {}
    try:
        nemotron_interpretations = orchestrate_vision_classification(
            t1_np=t1_dict["array"],
            t2_np=t2_dict["array"],
            regions=inference_result.regions
        )
    except Exception as e:
        logger.warning(f"Nemotron classification failed: {e}")

    detections_geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    # 7. Layers output
    layers = {}
    for layer_name in mission_config.get("layers", []):
        layers[layer_name] = LayerConfig(source="system", note="Pending implementation")
        
    t1_acq = TimeSeriesAcquisition(**t1_meta)
    t2_acq = TimeSeriesAcquisition(**t2_meta)
    intermediates = [TimeSeriesAcquisition(**m) for m in selection["intermediate"]]
    
    summary = AnalysisSummary(
        mean_change_probability=inference_result.mean_change_probability,
        total_change_area_km2=sum(r.area_km2 or r.approx_area_sq_km for r in inference_result.regions),
        num_regions=len(inference_result.regions),
        metrics_crs="EPSG:4326/UTM"
    )

    return AnalysisResult(
        aoi_id=hashlib.md5(json.dumps(req.aoi, sort_keys=True).encode()).hexdigest(),
        mission=req.mission,
        mode="live",
        t1=t1_acq,
        t2=t2_acq,
        images_compared=selection["images_compared"],
        intermediate_acquisitions=intermediates,
        event_date=event_date_str,
        summary=summary,
        detections_geojson=detections_geojson,
        layers=layers,
        nemotron_interpretations=nemotron_interpretations,
        generated_at=dt.datetime.utcnow().isoformat() + "Z",
        selection_reason=selection.get("reason"),
        context={"weather": weather_context} if weather_context else None,
        t1_preview_base64=inference_result.t1_preview_base64,
        t2_preview_base64=inference_result.t2_preview_base64,
        t1_grayscale_base64=getattr(inference_result, 't1_grayscale_base64', None),
        t2_grayscale_base64=getattr(inference_result, 't2_grayscale_base64', None),
        t1_false_color_base64=getattr(inference_result, 't1_false_color_base64', None),
        t2_false_color_base64=getattr(inference_result, 't2_false_color_base64', None),
        optical_base64=getattr(inference_result, 'optical_base64', None),
        optical_boxes_base64=getattr(inference_result, 'optical_boxes_base64', None),
        change_mask_base64=inference_result.change_mask_base64,
        confidence_heatmap_base64=inference_result.confidence_heatmap_base64,
        overlay_base64=inference_result.overlay_base64,
        change_boxes_base64=getattr(inference_result, 'change_boxes_base64', None)
    )
