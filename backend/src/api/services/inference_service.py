from dataclasses import dataclass
from typing import List, Optional, Tuple
import time
import torch
import torch.nn.functional as F
import numpy as np

from src.api.schemas import ChangedRegion
from src.api.services.model_service import ModelService
from src.api.services.change_analyzer import extract_changed_regions
from src.api.services.visualization import (
    sar_to_colorized,
    sar_to_grayscale,
    sar_dualpol_to_rgb,
    generate_change_mask_image,
    generate_heatmap_image,
    generate_overlay_image,
    draw_change_boxes,
    array_to_base64_jpeg,
    array_to_base64_png,
)


@dataclass
class InferenceResult:
    total_pixels: int
    changed_pixels: int
    change_percentage: float
    total_changed_area_sq_km: Optional[float]
    num_change_clusters: int
    regions: List[ChangedRegion]
    mean_change_probability: float
    
    t1_preview_base64: str
    t2_preview_base64: str
    t1_grayscale_base64: str
    t2_grayscale_base64: str
    t1_false_color_base64: str
    t2_false_color_base64: str
    change_mask_base64: str
    confidence_heatmap_base64: str
    overlay_base64: str
    change_boxes_base64: str


def run_change_detection(
    t1_np: np.ndarray,
    t2_np: np.ndarray,
    model_name: str,
    threshold: float,
    min_region_area_px: int,
    bbox: Optional[List[float]] = None,
) -> InferenceResult:
    """
    Shared inference and visualization logic.
    t1_np and t2_np should be normalized float32 arrays (C, H, W).
    """
    # Ensure T1 and T2 have the same dimensions by cropping to the minimum
    h1, w1 = t1_np.shape[1:]
    h2, w2 = t2_np.shape[1:]
    min_h, min_w = min(h1, h2), min(w1, w2)
    
    t1_np = t1_np[:, :min_h, :min_w]
    t2_np = t2_np[:, :min_h, :min_w]

    t1_tensor = torch.from_numpy(t1_np)
    t2_tensor = torch.from_numpy(t2_np)

    # Pad to multiple of 16 for UNet architectures
    pad_h = (16 - (min_h % 16)) % 16
    pad_w = (16 - (min_w % 16)) % 16
    if pad_h > 0 or pad_w > 0:
        t1_tensor = F.pad(t1_tensor, (0, pad_w, 0, pad_h))
        t2_tensor = F.pad(t2_tensor, (0, pad_w, 0, pad_h))

    model_service = ModelService.get_instance()
    prob_map, binary_mask = model_service.predict_change_sar(
        t1_tensor=t1_tensor,
        t2_tensor=t2_tensor,
        model_name=model_name,
        threshold=threshold,
    )
    
    # Crop back to original minimum dimensions
    if pad_h > 0 or pad_w > 0:
        prob_map = prob_map[:min_h, :min_w]
        binary_mask = binary_mask[:min_h, :min_w]

    regions, total_changed_km2 = extract_changed_regions(
        binary_mask=binary_mask,
        prob_map=prob_map,
        min_region_area_px=min_region_area_px,
        bbox=bbox,
    )

    # Calculate metrics
    total_px = binary_mask.size
    changed_px = int(np.sum(binary_mask > 0))
    change_pct = round((changed_px / total_px) * 100.0, 3) if total_px > 0 else 0.0
    mean_prob = float(np.mean(prob_map[binary_mask > 0])) if changed_px > 0 else 0.0

    # Visualization (display-only; never affects the inference outputs above)
    t1_color = sar_to_colorized(t1_np)
    t2_color = sar_to_colorized(t2_np)
    t1_gray = sar_to_grayscale(t1_np)
    t2_gray = sar_to_grayscale(t2_np)
    t1_fc = sar_dualpol_to_rgb(t1_np)
    t2_fc = sar_dualpol_to_rgb(t2_np)

    mask_rgb = generate_change_mask_image(binary_mask)
    heatmap_rgb = generate_heatmap_image(prob_map, colormap_name="turbo")
    overlay_rgb = generate_overlay_image(t2_color, binary_mask)
    boxes_rgb = draw_change_boxes(t2_color, regions)

    t1_b64 = array_to_base64_jpeg(t1_color)
    t2_b64 = array_to_base64_jpeg(t2_color)
    t1_gray_b64 = array_to_base64_jpeg(t1_gray)
    t2_gray_b64 = array_to_base64_jpeg(t2_gray)
    t1_fc_b64 = array_to_base64_jpeg(t1_fc)
    t2_fc_b64 = array_to_base64_jpeg(t2_fc)
    mask_b64 = array_to_base64_png(mask_rgb)
    heatmap_b64 = array_to_base64_jpeg(heatmap_rgb)
    overlay_b64 = array_to_base64_jpeg(overlay_rgb)
    boxes_b64 = array_to_base64_jpeg(boxes_rgb)

    return InferenceResult(
        total_pixels=total_px,
        changed_pixels=changed_px,
        change_percentage=change_pct,
        total_changed_area_sq_km=total_changed_km2,
        num_change_clusters=len(regions),
        regions=regions,
        mean_change_probability=mean_prob,
        t1_preview_base64=t1_b64,
        t2_preview_base64=t2_b64,
        t1_grayscale_base64=t1_gray_b64,
        t2_grayscale_base64=t2_gray_b64,
        t1_false_color_base64=t1_fc_b64,
        t2_false_color_base64=t2_fc_b64,
        change_mask_base64=mask_b64,
        confidence_heatmap_base64=heatmap_b64,
        overlay_base64=overlay_b64,
        change_boxes_base64=boxes_b64,
    )
