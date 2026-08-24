"""
src/api/routers/detect.py
=========================
Change Detection endpoints:
- Automated Sentinel-1 SAR change detection from coordinates
- Custom uploaded image pair change detection
"""

from __future__ import annotations

import io
import time
from typing import Optional
import numpy as np
from PIL import Image
import torch
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from src.api.schemas import (
    ChangeDetectionResponse,
    DetectSentinelRequest,
)
from src.data_ingestion.sentinel_client import (
    fetch_sentinel1_pair,
    SentinelAPIError,
)
from src.data_ingestion.optical_client import fetch_optical_basemap
from src.api.services.model_service import ModelService
from src.api.services.change_analyzer import extract_changed_regions
from src.api.services.visualization import (
    array_to_base64_png,
    array_to_base64_jpeg,
    generate_change_mask_image,
    generate_heatmap_image,
    generate_overlay_image,
    sar_dualpol_to_rgb,
    sar_to_grayscale,
    sar_to_colorized,
    draw_change_boxes,
)
from src.preprocessing.sar_loader import load_sar_pair_for_inference

router = APIRouter(prefix="/detect", tags=["Change Detection"])


@router.post(
    "/sentinel",
    response_model=ChangeDetectionResponse,
    summary="End-to-End Sentinel-1 Change Intelligence",
)
async def detect_sentinel_changes(req: DetectSentinelRequest) -> ChangeDetectionResponse:
    """
    Automated Sentinel-1 Change Detection:
    1. Fetches dual-polarization SAR imagery for T1 and T2 from Copernicus CDSE.
    2. Runs forward inference through Siamese Change Detection neural network.
    3. Identifies changed clusters, geographic coordinates, and severity levels.
    4. Generates false-color SAR previews, binary masks, and confidence heatmaps.
    """
    t0 = time.perf_counter()
    try:
        # Validate the requested model before any (expensive) data ingestion.
        if req.model_name not in ["snunet_cd_sar"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{req.model_name}' is not allowed or has no trained checkpoint."
            )

        # Step 1: Ingestion from CDSE
        t1_np, t2_np = fetch_sentinel1_pair(
            bbox=req.bbox.to_list(),
            date_t1_range=req.date_range_t1,
            date_t2_range=req.date_range_t2,
            output_resolution=req.resolution,
        )
        # fetch_sentinel1_pair returns normalized float32 np.ndarray (2, H, W)
        t1_tensor = torch.from_numpy(t1_np)
        t2_tensor = torch.from_numpy(t2_np)

        # Step 2: Model Inference
        model_service = ModelService.get_instance()
        try:
            prob_map, binary_mask = model_service.predict_change_sar(
                t1_tensor=t1_tensor,
                t2_tensor=t2_tensor,
                model_name=req.model_name,
                threshold=req.threshold,
            )
        except ValueError as ve:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(ve),
            )

        # Step 3: Intelligence & Region Analysis
        regions, total_changed_km2 = extract_changed_regions(
            binary_mask=binary_mask,
            prob_map=prob_map,
            min_region_area_px=req.min_region_area_px,
            bbox=req.bbox.to_list(),
        )

        # Step 4: Visualizations (display-only; never affects inference above)
        # Default previews: colorized "satellite-style" SAR (readable, natural
        # earth tones). Grayscale and dual-pol false color are optional layers.
        t1_color = sar_to_colorized(t1_np)
        t2_color = sar_to_colorized(t2_np)
        t1_gray = sar_to_grayscale(t1_np)
        t2_gray = sar_to_grayscale(t2_np)
        t1_fc = sar_dualpol_to_rgb(t1_np)
        t2_fc = sar_dualpol_to_rgb(t2_np)
        mask_rgb = generate_change_mask_image(binary_mask)
        heatmap_rgb = generate_heatmap_image(prob_map, colormap_name="turbo")
        # Overlay: highlight detected changes over the readable colorized background.
        overlay_rgb = generate_overlay_image(t2_color, binary_mask)
        # "Highlight Changes": labeled severity-colored boxes over colorized T2.
        boxes_rgb = draw_change_boxes(t2_color, regions)

        # Optional true-color optical basemap for this AOI (display-only, best-effort).
        # Aligned to the SAR grid so the change boxes overlay correctly. Returns
        # None on any failure so the optical layer is simply omitted.
        optical_b64 = None
        optical_boxes_b64 = None
        optical_rgb = fetch_optical_basemap(req.bbox.to_list(), t2_np.shape[1:])
        if optical_rgb is not None:
            optical_b64 = array_to_base64_jpeg(optical_rgb)
            optical_boxes_b64 = array_to_base64_jpeg(draw_change_boxes(optical_rgb, regions))

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

        total_px = binary_mask.size
        changed_px = int(np.sum(binary_mask > 0))
        change_pct = round((changed_px / total_px) * 100.0, 3)
        elapsed = round(time.perf_counter() - t0, 3)

        return ChangeDetectionResponse(
            status="success",
            model_used=req.model_name,
            threshold=req.threshold,
            total_pixels=total_px,
            changed_pixels=changed_px,
            change_percentage=change_pct,
            total_changed_area_sq_km=total_changed_km2,
            num_change_clusters=len(regions),
            regions=regions,
            t1_preview_base64=t1_b64,
            t2_preview_base64=t2_b64,
            t1_grayscale_base64=t1_gray_b64,
            t2_grayscale_base64=t2_gray_b64,
            t1_false_color_base64=t1_fc_b64,
            t2_false_color_base64=t2_fc_b64,
            optical_base64=optical_b64,
            optical_boxes_base64=optical_boxes_b64,
            change_mask_base64=mask_b64,
            confidence_heatmap_base64=heatmap_b64,
            overlay_base64=overlay_b64,
            change_boxes_base64=boxes_b64,
            execution_time_sec=elapsed,
        )

    except HTTPException:
        # Deliberate 4xx/5xx (e.g. model refusal 400, missing checkpoint 503)
        # must propagate unchanged rather than be masked as a generic 500.
        raise
    except SentinelAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Sentinel API error: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Change detection failed: {e}",
        )


@router.post(
    "/upload",
    response_model=ChangeDetectionResponse,
    summary="Change Detection on Uploaded Image Pair",
)
async def detect_uploaded_images(
    image_t1: UploadFile = File(..., description="Reference (T1) image file (PNG/JPEG)"),
    image_t2: UploadFile = File(..., description="Target (T2) image file (PNG/JPEG)"),
    model_name: str = Form("snunet_cd_sar", description="Model architecture: 'snunet_cd_sar'"),
    threshold: float = Form(0.5, ge=0.0, le=1.0, description="Decision threshold"),
    min_region_area_px: int = Form(10, ge=1, description="Minimum cluster pixel area"),
) -> ChangeDetectionResponse:
    """
    Change Detection on custom uploaded image pair (RGB or Grayscale).
    """
    t0 = time.perf_counter()
    try:
        t1_bytes = await image_t1.read()
        t2_bytes = await image_t2.read()

        pil_t1 = Image.open(io.BytesIO(t1_bytes)).convert("RGB")
        pil_t2 = Image.open(io.BytesIO(t2_bytes)).convert("RGB")

        # Standardize size (ensure same dimensions)
        if pil_t1.size != pil_t2.size:
            pil_t2 = pil_t2.resize(pil_t1.size, Image.Resampling.BILINEAR)

        # Convert to tensor [3, H, W] in [0, 1]
        t1_np = np.array(pil_t1, dtype=np.float32) / 255.0
        t2_np = np.array(pil_t2, dtype=np.float32) / 255.0

        t1_tensor = torch.from_numpy(t1_np).permute(2, 0, 1)
        t2_tensor = torch.from_numpy(t2_np).permute(2, 0, 1)

        if model_name not in ["snunet_cd_sar"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{model_name}' is not allowed or has no trained checkpoint."
            )

        model_service = ModelService.get_instance()
        try:
            prob_map, binary_mask = model_service.predict_change_rgb(
                t1_tensor=t1_tensor,
                t2_tensor=t2_tensor,
                model_name=model_name,
                threshold=threshold,
            )
        except ValueError as ve:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(ve),
            )

        regions, _ = extract_changed_regions(
            binary_mask=binary_mask,
            prob_map=prob_map,
            min_region_area_px=min_region_area_px,
        )

        mask_rgb = generate_change_mask_image(binary_mask)
        heatmap_rgb = generate_heatmap_image(prob_map, colormap_name="turbo")
        overlay_rgb = generate_overlay_image((t2_np * 255).astype(np.uint8), binary_mask)

        t1_b64 = array_to_base64_jpeg((t1_np * 255).astype(np.uint8))
        t2_b64 = array_to_base64_jpeg((t2_np * 255).astype(np.uint8))
        mask_b64 = array_to_base64_png(mask_rgb)
        heatmap_b64 = array_to_base64_jpeg(heatmap_rgb)
        overlay_b64 = array_to_base64_jpeg(overlay_rgb)

        total_px = binary_mask.size
        changed_px = int(np.sum(binary_mask > 0))
        change_pct = round((changed_px / total_px) * 100.0, 3)
        elapsed = round(time.perf_counter() - t0, 3)

        return ChangeDetectionResponse(
            status="success",
            model_used=model_name,
            threshold=threshold,
            total_pixels=total_px,
            changed_pixels=changed_px,
            change_percentage=change_pct,
            total_changed_area_sq_km=None,
            num_change_clusters=len(regions),
            regions=regions,
            t1_preview_base64=t1_b64,
            t2_preview_base64=t2_b64,
            change_mask_base64=mask_b64,
            confidence_heatmap_base64=heatmap_b64,
            overlay_base64=overlay_b64,
            execution_time_sec=elapsed,
        )

    except HTTPException:
        # Preserve deliberate refusals (400 unknown model, 503 missing checkpoint).
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference on uploaded images failed: {e}",
        )


@router.post(
    "/change-detection",
    response_model=ChangeDetectionResponse,
    summary="Change Detection on Uploaded SAR TIFF Pair",
)
async def detect_sar_changes_from_upload(
    image_t1: UploadFile = File(..., description="Reference (T1) SAR image file (.tif)"),
    image_t2: UploadFile = File(..., description="Target (T2) SAR image file (.tif)"),
    threshold: float = Form(0.95, ge=0.0, le=1.0, description="Decision threshold"),
    min_region_area_px: int = Form(10, ge=1, description="Minimum cluster pixel area"),
) -> ChangeDetectionResponse:
    """
    Change Detection on custom uploaded Sentinel-1 SAR image pair (TIFF format).
    Uses exactly the same preprocessing as SNUNet-CD Model 3 training.
    """
    t0 = time.perf_counter()
    try:
        t1_bytes = await image_t1.read()
        t2_bytes = await image_t2.read()

        import torch.nn.functional as F
        
        # Phase 1 requirement: Use exact preprocessing from training (is_linear=False for TUM OSCD)
        # load_sar_pair_for_inference returns (t1_tensor, t2_tensor, valid_t1, valid_t2) if return_validity_mask=True
        t1_np, t2_np = load_sar_pair_for_inference(
            t1_bytes,
            t2_bytes,
            is_linear=False,
            return_tensors=False,
        )
        
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
            model_name="snunet_cd_sar",
            threshold=threshold,
        )
        
        # Crop back to original minimum dimensions
        if pad_h > 0 or pad_w > 0:
            prob_map = prob_map[:min_h, :min_w]
            binary_mask = binary_mask[:min_h, :min_w]

        regions, _ = extract_changed_regions(
            binary_mask=binary_mask,
            prob_map=prob_map,
            min_region_area_px=min_region_area_px,
        )

        # Ensure spatial consistency
        if t1_np.shape[1:] != binary_mask.shape:
            # Mask generation should match input shape, but just in case
            pass

        # Visualization (display-only; never affects the inference outputs above)
        # Default previews: colorized "satellite-style" SAR (readable, natural
        # earth tones). Grayscale and dual-pol false color are optional layers.
        t1_color = sar_to_colorized(t1_np)
        t2_color = sar_to_colorized(t2_np)
        t1_gray = sar_to_grayscale(t1_np)
        t2_gray = sar_to_grayscale(t2_np)
        t1_fc = sar_dualpol_to_rgb(t1_np)
        t2_fc = sar_dualpol_to_rgb(t2_np)

        mask_rgb = generate_change_mask_image(binary_mask)
        heatmap_rgb = generate_heatmap_image(prob_map, colormap_name="turbo")
        # Overlay: highlight detected changes over the readable colorized background.
        overlay_rgb = generate_overlay_image(t2_color, binary_mask)
        # "Highlight Changes": labeled severity-colored boxes over colorized T2.
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

        total_px = binary_mask.size
        changed_px = int(np.sum(binary_mask > 0))
        change_pct = round((changed_px / total_px) * 100.0, 3) if total_px > 0 else 0.0
        elapsed = round(time.perf_counter() - t0, 3)

        return ChangeDetectionResponse(
            status="success",
            model_used="snunet_cd_sar",
            threshold=threshold,
            total_pixels=total_px,
            changed_pixels=changed_px,
            change_percentage=change_pct,
            total_changed_area_sq_km=None,
            num_change_clusters=len(regions),
            regions=regions,
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
            execution_time_sec=elapsed,
        )

    except HTTPException:
        # Preserve deliberate refusals rather than masking them as a 500.
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SAR Inference on uploaded images failed: {e}",
        )
