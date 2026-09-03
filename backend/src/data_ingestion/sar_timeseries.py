from __future__ import annotations

from collections import defaultdict
import datetime as dt
import logging

from src.data_ingestion.sentinel_client import (
    CDSEAuthManager,
    SentinelHubClient,
)
from src.preprocessing.sar_loader import (
    decode_geotiff_response,
    normalize_sar_tensor,
)

logger = logging.getLogger(__name__)


def select_acquisitions(
    candidates: list[dict],
    strategy: str = "progressive",
    event_date: dt.date | None = None
) -> dict:
    """
    Select the optimal T1/T2 pair based on a deterministic preference order:
    full AOI coverage (assumed via STAC bbox query) -> IW/GRD -> VV+VH -> same orbit direction -> same relative orbit.
    """
    # 1. Sort chronologically
    candidates.sort(key=lambda x: dt.datetime.fromisoformat(x["acquisition_date"].replace("Z", "+00:00")))
    
    # Filter 1: IW mode and both VV/VH polarizations
    # We also assume GRD since the STAC collection is sentinel-1-grd
    valid_candidates = []
    for c in candidates:
        if c.get("mode") != "IW":
            continue
        pols = [p.upper() for p in c.get("polarizations", [])]
        if "VV" not in pols or "VH" not in pols:
            continue
        valid_candidates.append(c)
        
    if len(valid_candidates) < 2:
        return {
            "t1": None, "t2": None, "intermediate": [], 
            "images_compared": 0, "strategy": strategy,
            "reason": f"Insufficient valid scenes (need 2, found {len(valid_candidates)} after IW/VV+VH filter)"
        }
        
    # Filter 2: Deduplicate (no scenes < 24 hours apart)
    deduped = []
    last_date = None
    for c in valid_candidates:
        current_date = dt.datetime.fromisoformat(c["acquisition_date"].replace("Z", "+00:00"))
        if last_date is not None and (current_date - last_date).total_seconds() < 86400:
            continue
        deduped.append(c)
        last_date = current_date
        
    if len(deduped) < 2:
        return {
            "t1": None, "t2": None, "intermediate": [], 
            "images_compared": 0, "strategy": strategy,
            "reason": "Insufficient scenes after 24h deduplication"
        }

    # Group by (orbit_state, relative_orbit)
    groups = defaultdict(list)
    for c in deduped:
        key = (c.get("orbit_state"), c.get("relative_orbit"))
        groups[key].append(c)
        
    # Find group with widest temporal span covering the period
    best_group = None
    max_span = -1
    
    for key, members in groups.items():
        if len(members) < 2:
            continue
        span = (dt.datetime.fromisoformat(members[-1]["acquisition_date"].replace("Z", "+00:00")) - 
                dt.datetime.fromisoformat(members[0]["acquisition_date"].replace("Z", "+00:00"))).total_seconds()
        
        if span > max_span:
            max_span = span
            best_group = members
            
    # If no group has >= 2 scenes with same orbit_state and relative_orbit, 
    # relax requirement: just same orbit_state
    if best_group is None:
        orbit_groups = defaultdict(list)
        for c in deduped:
            orbit_groups[c.get("orbit_state")].append(c)
            
        for key, members in orbit_groups.items():
            if len(members) < 2:
                continue
            span = (dt.datetime.fromisoformat(members[-1]["acquisition_date"].replace("Z", "+00:00")) - 
                    dt.datetime.fromisoformat(members[0]["acquisition_date"].replace("Z", "+00:00"))).total_seconds()
            
            if span > max_span:
                max_span = span
                best_group = members
                
        reason = "Selected based on same orbit_state (relaxed relative_orbit due to insufficient scenes)"
    else:
        reason = "Selected based on strict match: IW/GRD, VV+VH, same orbit_state, same relative_orbit"
        
    # If still no group has >= 2 scenes, fallback to just any 2 valid deduped scenes
    if best_group is None:
        best_group = deduped
        reason = "Fallback: selected any valid IW/GRD VV+VH scenes (mismatched orbit_state/relative_orbit)"
        
    # Selection Strategy
    # For P0, we are ONLY supporting progressive
    if strategy == "progressive":
        t1 = best_group[0]
        t2 = best_group[-1]
        intermediate = best_group[1:-1]
    else:
        # P0 spec upgrade: "Do NOT invent/mock a weather event date inside production logic. 
        # For P0, support progressive oldest->latest only."
        t1 = best_group[0]
        t2 = best_group[-1]
        intermediate = best_group[1:-1]
        strategy = "progressive (fallback from event-anchored for P0)"

    return {
        "t1": t1,
        "t2": t2,
        "intermediate": intermediate,
        "images_compared": 2,
        "strategy": strategy,
        "reason": reason
    }


def fetch_sar_timeseries(
    bbox: list[float],
    date_range: tuple[str, str],
    output_resolution: tuple[int, int] = (512, 512),
    max_scenes: int = 10,
    auth: CDSEAuthManager | None = None,
    strategy: str = "progressive",
    event_date: dt.date | None = None
) -> tuple[dict, dict, dict, dict]:
    """
    Fetch metadata for a time series of Sentinel-1 GeoTIFFs, but ONLY decode and normalize the selected T1/T2 pair.

    Returns:
        A tuple of (selection_result, oldest_dict, latest_dict, all_metadata_list).
    """
    if auth is None:
        auth = CDSEAuthManager()

    client = SentinelHubClient(auth)

    # 1. Fetch metadata for all scenes in the date range
    all_metadata = client.fetch_all_scene_metadata(
        bbox=bbox, 
        date_range=date_range
    )
    
    # 2. Select acquisitions
    selection = select_acquisitions(all_metadata, strategy, event_date)
    
    if selection["t1"] is None or selection["t2"] is None:
        raise ValueError(
            f"Could not select valid T1/T2 pair. Reason: {selection['reason']}"
        )

    # 3. Fetch and decode ONLY the T1 and T2 scenes
    oldest_meta = selection["t1"]
    latest_meta = selection["t2"]

    results = []
    for meta in [oldest_meta, latest_meta]:
        logger.info(f"Fetching tile for scene {meta['scene_id']} at {meta['acquisition_date']}")
        raw_bytes = client.fetch_tile(
            bbox=bbox,
            exact_datetime=meta["acquisition_date"],
            output_resolution=output_resolution,
        )
        
        # Exact locked preprocessing pipeline
        sar_array, valid_mask = decode_geotiff_response(raw_bytes, return_validity=True)
        normalized_array = normalize_sar_tensor(
            sar_array, 
            is_linear=False, 
            return_validity=False
        )
        
        results.append({
            "meta": meta,
            "array": normalized_array,
            "valid_mask": valid_mask,
        })
        
    return selection, results[0], results[1], all_metadata
