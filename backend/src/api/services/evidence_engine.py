from typing import List, Optional
import math
from src.api.schemas import ChangedRegion, EvidenceObject, EvidenceSignal, ContextLayers

def _normalize_metric(val: float, min_val: float, max_val: float, clamp: bool = True) -> float:
    if max_val == min_val:
        return 0.0
    norm = (val - min_val) / (max_val - min_val)
    if clamp:
        norm = max(0.0, min(1.0, norm))
    return norm

def synthesize_evidence(
    region: ChangedRegion,
    dem_context: Optional[dict] = None,
    landcover_context: Optional[dict] = None,
    fire_context: Optional[dict] = None,
    surface_water_context: Optional[dict] = None,
    osm_context: Optional[dict] = None,
    mission_config: Optional[dict] = None
) -> EvidenceObject:
    """
    Synthesizes available metrics into a structured EvidenceObject.
    Does not penalize for missing layers (e.g. fire/weather), only scores what is available.
    """
    signals: List[EvidenceSignal] = []
    score_components = []
    caveats = []
    
    # 1. SAR Primary Signal
    sar_prob = region.change_probability
    sar_norm = sar_prob  # already 0-1
    sar_weight = 1.0
    signals.append(EvidenceSignal(
        name="sar_backscatter_anomaly",
        source="snunet_cd_sar",
        value=round(sar_prob, 4),
        normalized=round(sar_norm, 4),
        weight=sar_weight
    ))
    score_components.append(sar_norm * sar_weight)
    
    # 2. Area Signal
    # Larger areas are higher confidence of actual change vs noise
    area_km2 = region.area_km2 or region.approx_area_sq_km or 0.0
    # Normalize area: 0 km2 = 0.0, 1.0 km2 = 1.0
    area_norm = _normalize_metric(area_km2, min_val=0.001, max_val=1.0)
    area_weight = 0.5
    signals.append(EvidenceSignal(
        name="spatial_extent",
        source="geometry",
        value=round(area_km2, 6),
        normalized=round(area_norm, 4),
        weight=area_weight
    ))
    score_components.append(area_norm * area_weight)
    
    # 3. Terrain Context
    if dem_context:
        slope = dem_context.get("mean_slope_deg", 0.0)
        overlap = dem_context.get("layover_shadow_overlap_pct", 0.0)
        
        if overlap > 10.0:
            caveats.append(f"High risk of SAR geometric distortion (Layover/Shadow overlap: {overlap}%)")
            
        # Slope penalty (SAR is less reliable on steep slopes)
        if slope > 15.0:
            caveats.append(f"Steep terrain ({slope} deg) may cause radiometric distortion.")
            slope_penalty_norm = _normalize_metric(slope, 15.0, 45.0)
            # Negative weight signal
            signals.append(EvidenceSignal(
                name="terrain_distortion_risk",
                source="copernicus_dem_30",
                value=round(slope, 2),
                normalized=round(slope_penalty_norm, 4),
                weight=-0.5
            ))
            score_components.append(-slope_penalty_norm * 0.5)
            
    # 4. Landcover Context
    if landcover_context:
        is_crop = landcover_context.get("is_cropland_dominant", False)
        is_tree = landcover_context.get("is_tree_consistent", False)
        is_built = landcover_context.get("is_sparse_built_consistent", False)
        dom_class = landcover_context.get("dominant_class", "Unknown")
        
        if is_crop:
            caveats.append("Possible agricultural/seasonal surface change.")
            crop_penalty_norm = 1.0
            signals.append(EvidenceSignal(
                name="cropland_seasonal_risk",
                source="esa_worldcover_10m",
                value=dom_class,
                normalized=crop_penalty_norm,
                weight=-0.5
            ))
            score_components.append(-crop_penalty_norm * 0.5)
            
        if mission_config:
            mission_name = mission_config.get("name", "").lower()
            if "forest" in mission_name or "deforestation" in mission_name:
                if not is_tree:
                    caveats.append(f"Region is {dom_class}, not consistent with expected tree-cover context.")
            elif "mining" in mission_name or "disturbance" in mission_name:
                if not is_built:
                    caveats.append(f"Region is {dom_class}, not consistent with bare/sparse or built-up context.")
                    
    # 5. Fire Context
    if fire_context:
        is_nearby = fire_context.get("nearby", False)
        if is_nearby:
            caveats.append("FIRMS thermal anomaly detected nearby. May be wildfire, active burning, or industrial flare.")
            # Note: Fire context adds evidence but does not change the base SAR probability.
            signals.append(EvidenceSignal(
                name="active_fire_detected",
                source="nasa_firms",
                value=fire_context.get("count", 1),
                normalized=1.0,
                weight=0.5
            ))
            score_components.append(1.0 * 0.5)

    # 6. Surface Water Context
    if surface_water_context:
        new_water = surface_water_context.get("new_water_km2", 0.0)
        if new_water > 0:
            caveats.append("Potential flood-related surface change.")
            signals.append(EvidenceSignal(
                name="new_surface_water_detected",
                source="sar_t2_vv",
                value=new_water,
                normalized=min(new_water / 0.1, 1.0), # normalize to 10 hectares max contribution
                weight=0.5
            ))
            score_components.append(min(new_water / 0.1, 1.0) * 0.5)

    # 7. OSM Context
    if osm_context:
        if osm_context.get("industrial"):
            caveats.append("Proximity to industrial area detected.")
            
        road_dist = osm_context.get("nearest_road_m")
        if road_dist is not None and road_dist < 100:
            mission_type = mission_config.get("name", "general").lower() if mission_config else "general"
            if mission_type in ["mining", "infrastructure"]:
                signals.append(EvidenceSignal(
                    name="osm_road_context",
                    source="OpenStreetMap",
                    value="Nearby access road",
                    normalized=0.2,
                    weight=0.5
                ))
                score_components.append(0.2 * 0.5)
                caveats.append("Proximity to access road suggests possible human-driven disturbance (verification required).")

    # Calculate weighted average
    total_weight = sum(abs(s.weight) for s in signals)
    raw_score = sum(score_components)
    final_score = max(0.0, min(1.0, raw_score / total_weight)) if total_weight > 0 else 0.0
    
    # Determine Strength and Interpretation
    if final_score > 0.8:
        strength = "HIGH"
        interp = "Strong multi-factor evidence of ground disturbance."
    elif final_score > 0.5:
        strength = "MEDIUM"
        interp = "Moderate evidence of surface change."
    else:
        strength = "LOW"
        interp = "Weak or contested evidence. High likelihood of noise or seasonal artifact."
        
    if mission_config:
        mission_name = mission_config.get("name", "Unknown")
        interp += f" Evaluated under {mission_name} parameters."
        
    context = ContextLayers(
        dem=dem_context,
        landcover=landcover_context,
        fire=fire_context,
        surface_water=surface_water_context,
        osm=osm_context
    )
        
    return EvidenceObject(
        evidence_score=round(final_score, 4),
        evidence_strength=strength,
        interpretation=interp,
        signals=signals,
        caveats=caveats,
        context=context
    )
