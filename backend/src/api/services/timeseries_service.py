from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

from src.api.services.inference_service import run_change_detection, InferenceResult

logger = logging.getLogger(__name__)


@dataclass
class PairwiseResult:
    t1_meta: dict
    t2_meta: dict
    inference_result: InferenceResult


def run_timeseries_change_detection(
    acquisitions: list[dict],
    model_name: str,
    threshold: float,
    min_region_area_px: int,
) -> List[PairwiseResult]:
    """
    Run sequential pairwise change detection over a time series of SAR acquisitions.
    
    Args:
        acquisitions: List of dicts from `fetch_sar_timeseries`.
        model_name: Name of the loaded SNUNet model (e.g. "snunet_cd_sar").
        threshold: Probability threshold for binary mask.
        min_region_area_px: Minimum cluster area to keep.
        
    Returns:
        List of PairwiseResult containing metadata and InferenceResult for each consecutive pair.
    """
    if len(acquisitions) < 2:
        raise ValueError("At least 2 acquisitions are required for time-series change detection.")
        
    results = []
    
    for i in range(len(acquisitions) - 1):
        t1 = acquisitions[i]
        t2 = acquisitions[i + 1]
        
        logger.info(f"Running inference for pair {i+1}/{len(acquisitions)-1}: "
                    f"{t1['meta']['acquisition_date']} -> {t2['meta']['acquisition_date']}")
        
        inference_result = run_change_detection(
            t1_np=t1["array"],
            t2_np=t2["array"],
            model_name=model_name,
            threshold=threshold,
            min_region_area_px=min_region_area_px
        )
        
        results.append(PairwiseResult(
            t1_meta=t1["meta"],
            t2_meta=t2["meta"],
            inference_result=inference_result,
        ))
        
    return results
