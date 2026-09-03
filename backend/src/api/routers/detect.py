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
    AvailabilityResponse,
    TimeSeriesRequest,
    TimeSeriesResponse,
    TimeSeriesAcquisition,
    PairwiseChangeResult,
    AnalyzeRequest,
    AnalysisResult,
)
from src.data_ingestion.sentinel_client import (
    fetch_sentinel1_pair,
    SentinelAPIError,
)
from src.data_ingestion.sar_timeseries import fetch_sar_timeseries
from src.data_ingestion.optical_client import fetch_optical_basemap
from src.api.services.model_service import ModelService
from src.api.services.change_analyzer import extract_changed_regions
from src.api import db
from sqlalchemy.orm import Session
from src.api.models import SARScene, ChangeDetectionJob, Detection
import datetime as dt
from src.api.services.visualization import (
    array_to_base64_jpeg,
    array_to_base64_png,
    draw_change_boxes,
    generate_change_mask_image,
    generate_heatmap_image,
    generate_overlay_image,
)
from src.preprocessing.sar_loader import load_sar_pair_for_inference
from src.api.services.inference_service import run_change_detection
from src.api.services.timeseries_service import run_timeseries_change_detection
from src.api.services.analyze_service import run_analysis, load_missions

router = APIRouter(prefix="/detect", tags=["Change Detection"])


def _get_or_create_scene(session: Session, meta: dict) -> SARScene:
    scene = session.query(SARScene).filter_by(
        provider=meta["provider"],
        scene_id=meta["scene_id"]
    ).first()
    
    if not scene:
        acq_date = dt.datetime.fromisoformat(meta["acquisition_date"].replace("Z", "+00:00"))
        bbox = meta.get("bbox")
        
        scene = SARScene(
            provider=meta["provider"],
            scene_id=meta["scene_id"],
            acquisition_date=acq_date,
            bbox_min_lon=bbox[0] if bbox else None,
            bbox_min_lat=bbox[1] if bbox else None,
            bbox_max_lon=bbox[2] if bbox else None,
            bbox_max_lat=bbox[3] if bbox else None,
            status="created"
        )
        session.add(scene)
        session.commit()
        session.refresh(scene)
        
    return scene


@router.post(
    "/availability",
    response_model=AvailabilityResponse,
    summary="Check Satellite Imagery Availability",
)
async def check_availability(req: DetectSentinelRequest) -> AvailabilityResponse:
    """
    Check if Sentinel-1 SAR imagery is available for the given location and dates.
    This is a lightweight metadata check that does not run inference.
    """
    try:
        from src.data_ingestion.sentinel_client import SentinelHubClient, CDSEAuthManager
        client = SentinelHubClient(CDSEAuthManager())
        t1_meta = client.fetch_scene_metadata(req.bbox.to_list(), req.date_range_t1)
        t2_meta = client.fetch_scene_metadata(req.bbox.to_list(), req.date_range_t2)
        
        return {
            "t1_scene": t1_meta,
            "t2_scene": t2_meta
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Availability check failed: {str(exc)}")


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
    4. Generates false-color SAR previews, binary masks, and probability heatmaps.
    """
    t0 = time.perf_counter()
    try:
        # Validate the requested model before any (expensive) data ingestion.
        if req.model_name not in ["snunet_cd_sar"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{req.model_name}' is not allowed or has no trained checkpoint."
            )

        db.init_db()
        if db.SessionLocal is None:
            raise HTTPException(
                status_code=500,
                detail="Database is not configured",
            )
        session: Session = db.SessionLocal()
        job = None
        job_id = None

        try:
            from src.data_ingestion.sentinel_client import SentinelHubClient, CDSEAuthManager
            from src.api.models import SARAsset
            from src.storage.object_storage import download_bytes

            client = SentinelHubClient(CDSEAuthManager())
            t1_meta = client.fetch_scene_metadata(req.bbox.to_list(), req.date_range_t1)
            t2_meta = client.fetch_scene_metadata(req.bbox.to_list(), req.date_range_t2)

            # Resolve/create SARScene records
            t1_scene = _get_or_create_scene(session, t1_meta)
            t2_scene = _get_or_create_scene(session, t2_meta)

            t1_asset = session.query(SARAsset).filter_by(scene_id=t1_scene.id, time_label="T1").first()
            t2_asset = session.query(SARAsset).filter_by(scene_id=t2_scene.id, time_label="T2").first()

            t2_transform = None
            t2_crs = None

            metadata_extraction_ms = 0.0
            download_ms = 0.0
            preprocessing_ms = 0.0

            if t1_asset and t2_asset:
                from src.preprocessing.sar_loader import extract_geotiff_metadata
                
                t_start_download = time.perf_counter()
                t1_bytes = download_bytes(t1_asset.storage_key)
                t2_bytes = download_bytes(t2_asset.storage_key)
                download_ms = (time.perf_counter() - t_start_download) * 1000.0
                
                t_start_preprocessing = time.perf_counter()
                t1_np, t2_np = load_sar_pair_for_inference(t1_bytes, t2_bytes, is_linear=False, return_tensors=False)
                preprocessing_ms = (time.perf_counter() - t_start_preprocessing) * 1000.0
                
                t_start_metadata = time.perf_counter()
                geo_meta = extract_geotiff_metadata(t2_bytes)
                t2_transform = geo_meta.get("transform")
                t2_crs = geo_meta.get("crs")
                metadata_extraction_ms = (time.perf_counter() - t_start_metadata) * 1000.0
            else:
                # Fallback to direct download if assets aren't explicitly saved
                t1_np, t2_np, _, t2_meta, metadata_extraction_ms, download_ms, preprocessing_ms = fetch_sentinel1_pair(
                    bbox=req.bbox.to_list(),
                    date_t1_range=req.date_range_t1,
                    date_t2_range=req.date_range_t2,
                    output_resolution=req.resolution,
                )
                
                t2_raster_meta = t2_meta.get("raster_metadata", {})
                t2_transform = t2_raster_meta.get("transform")
                t2_crs = t2_raster_meta.get("crs")

            # Resolve/create SARScene records
            t1_scene = _get_or_create_scene(session, t1_meta)
            t2_scene = _get_or_create_scene(session, t2_meta)

            # Create ChangeDetectionJob
            job = ChangeDetectionJob(
                scene_before_id=t1_scene.id,
                scene_after_id=t2_scene.id,
                model_version=req.model_name,
                status="running"
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            job_id = job.id

            # Step 2: Shared Model Inference & Intelligence Extraction
            result = run_change_detection(
                t1_np=t1_np,
                t2_np=t2_np,
                model_name=req.model_name,
                threshold=req.threshold,
                min_region_area_px=req.min_region_area_px,
                bbox=req.bbox.to_list(),
                transform=t2_transform,
                crs=t2_crs,
            )

            job.status = "completed"
            job.change_percentage = result.change_percentage
            job.confidence = result.mean_change_probability
            metrics_dict = {
                "total_pixels": result.total_pixels,
                "changed_pixels": result.changed_pixels,
                "total_changed_area_sq_km": result.total_changed_area_sq_km,
                "num_change_clusters": result.num_change_clusters,
                "threshold": req.threshold,
                "mean_change_probability": result.mean_change_probability,
                "metadata_extraction_ms": metadata_extraction_ms,
                "download_ms": download_ms,
                "preprocessing_ms": preprocessing_ms,
                "model_inference_ms": result.model_inference_ms,
                "postprocessing_ms": result.postprocessing_ms,
            }
            job.metrics = metrics_dict
            session.commit()

            # Persist each Detection
            for region in result.regions:
                # Only save geometries if we have valid geo_bbox coordinates
                if region.geo_bbox:
                    # Valid GeoJSON Polygon must be a closed ring
                    coords = [
                        [
                            [region.geo_bbox[0], region.geo_bbox[1]],
                            [region.geo_bbox[2], region.geo_bbox[1]],
                            [region.geo_bbox[2], region.geo_bbox[3]],
                            [region.geo_bbox[0], region.geo_bbox[3]],
                            [region.geo_bbox[0], region.geo_bbox[1]],
                        ]
                    ]
                    geometry = {"type": "Polygon", "coordinates": coords}
                else:
                    # No fallback invalid geometry; just leave it null if missing (should not happen with good input)
                    geometry = None
                
                detection = Detection(
                    job_id=job_id,
                    geometry=geometry,
                    properties={
                        "region_id": region.region_id,
                        "area_px": region.area_px,
                        "approx_area_sq_km": region.approx_area_sq_km,
                        "mean_change_prob": region.mean_change_prob,
                        "severity": region.severity,
                        "label": region.label,
                    }
                )
                session.add(detection)
            session.commit()

        except ValueError as ve:
            if job_id is not None:
                try:
                    session.rollback()
                    failed_job = session.query(ChangeDetectionJob).get(job_id)
                    if failed_job:
                        failed_job.status = "failed"
                        failed_job.metrics = {"error": str(ve)}
                        session.commit()
                except Exception:
                    pass
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as exc:
            if job_id is not None:
                try:
                    session.rollback()
                    failed_job = session.query(ChangeDetectionJob).get(job_id)
                    if failed_job:
                        failed_job.status = "failed"
                        failed_job.metrics = {"error": str(exc)}
                        session.commit()
                except Exception:
                    pass
            raise HTTPException(status_code=500, detail=f"Change detection failed: {str(exc)}")

        finally:
            session.close()

        # Step 4: Visualizations (display-only; never affects inference above)
        # Optional true-color optical basemap for this AOI (display-only, best-effort).
        # Aligned to the SAR grid so the change boxes overlay correctly. Returns
        # None on any failure so the optical layer is simply omitted.
        optical_b64 = None
        optical_boxes_b64 = None
        optical_rgb, optical_fetch_ms, reprojection_ms = fetch_optical_basemap(
            req.bbox.to_list(),
            t2_np.shape[1:],
            target_crs=t2_crs,
            target_transform=t2_transform
        )
        if optical_rgb is not None:
            optical_b64 = array_to_base64_jpeg(optical_rgb)
            optical_boxes_b64 = array_to_base64_jpeg(draw_change_boxes(optical_rgb, result.regions))

        elapsed_sec = time.perf_counter() - t0
        total_ms = elapsed_sec * 1000.0
        
        # Update final metrics in DB (safe since we have job_id)
        if job_id is not None:
            # We must use a new session to update because the previous was closed in `finally:` block of `try`
            with db.SessionLocal() as update_session:
                final_job = update_session.query(ChangeDetectionJob).get(job_id)
                if final_job and isinstance(final_job.metrics, dict):
                    final_metrics = dict(final_job.metrics)
                    final_metrics["optical_fetch_ms"] = optical_fetch_ms
                    final_metrics["reprojection_ms"] = reprojection_ms
                    final_metrics["total_ms"] = total_ms
                    final_job.metrics = final_metrics
                    update_session.commit()

        elapsed = round(elapsed_sec, 3)

        # Phase N4 & N5: Nemotron Multimodal Classification (with context)
        from src.api.services.vision_pipeline import orchestrate_vision_classification
        import logging
        logger = logging.getLogger(__name__)
        
        nemotron_interpretations = {}
        try:
            nemotron_interpretations = orchestrate_vision_classification(
                t1_np=t1_np,
                t2_np=t2_np,
                regions=result.regions
            )
        except Exception as e:
            logger.warning(f"Nemotron classification failed in upload: {e}")

        return ChangeDetectionResponse(
            job_id=job_id,
            status="success",
            model_used=req.model_name,
            threshold=req.threshold,
            total_pixels=result.total_pixels,
            changed_pixels=result.changed_pixels,
            change_percentage=result.change_percentage,
            total_changed_area_sq_km=result.total_changed_area_sq_km,
            num_change_clusters=result.num_change_clusters,
            regions=result.regions,
            t1_preview_base64=result.t1_preview_base64,
            t2_preview_base64=result.t2_preview_base64,
            t1_grayscale_base64=result.t1_grayscale_base64,
            t2_grayscale_base64=result.t2_grayscale_base64,
            t1_false_color_base64=result.t1_false_color_base64,
            t2_false_color_base64=result.t2_false_color_base64,
            optical_base64=optical_b64,
            optical_boxes_base64=optical_boxes_b64,
            change_mask_base64=result.change_mask_base64,
            confidence_heatmap_base64=result.confidence_heatmap_base64,
            overlay_base64=result.overlay_base64,
            change_boxes_base64=result.change_boxes_base64,
            nemotron_interpretations=nemotron_interpretations,
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

        pil_t1 = Image.open(io.BytesIO(t1_bytes))
        pil_t2 = Image.open(io.BytesIO(t2_bytes))

        # Standardize size (ensure same dimensions)
        if pil_t1.size != pil_t2.size:
            pil_t2 = pil_t2.resize(pil_t1.size, Image.Resampling.BILINEAR)

        if model_name not in ["snunet_cd_sar", "changeformer_v6"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{model_name}' is not allowed or has no trained checkpoint."
            )

        # ── Channel validation ──────────────────────────
        t1_arr = np.array(pil_t1, dtype=np.float32)
        t2_arr = np.array(pil_t2, dtype=np.float32)

        # Determine channel count from the decoded arrays
        if t1_arr.ndim == 2:
            t1_channels = 1
        else:
            t1_channels = t1_arr.shape[2]

        if t2_arr.ndim == 2:
            t2_channels = 1
        else:
            t2_channels = t2_arr.shape[2]

        if model_name == "snunet_cd_sar":
            for label, ch in [("T1", t1_channels), ("T2", t2_channels)]:
                if ch == 3:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"{label} image has {ch} channels (RGB). "
                            f"Model 'snunet_cd_sar' requires exactly 2 channels "
                            f"(VV/VH SAR bands). Upload a 2-band GeoTIFF or two "
                            f"single-band grayscale images instead."
                        ),
                    )
                if ch not in (1, 2):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"{label} image has {ch} channels. "
                            f"Model 'snunet_cd_sar' requires exactly 2 channels (VV/VH)."
                        ),
                    )
        elif model_name == "changeformer_v6":
            for label, ch in [("T1", t1_channels), ("T2", t2_channels)]:
                if ch != 3 and ch != 4:  # Allowing 4 (RGBA) which PIL handles
                    # Check if it's 1-channel, we can convert but let's warn
                    pass

        # Normalize to [0, 1] float32
        # Determine max value based on dtype for proper normalization
        if t1_arr.max() > 1.0:
            t1_arr = t1_arr / 255.0
        if t2_arr.max() > 1.0:
            t2_arr = t2_arr / 255.0

        # Build tensors with correct channel layout
        if t1_channels == 1:
            # Grayscale: stack into 2 identical channels for snunet_cd_sar
            t1_tensor = torch.from_numpy(np.stack([t1_arr, t1_arr], axis=0))
        elif t1_channels == 2:
            t1_tensor = torch.from_numpy(t1_arr).permute(2, 0, 1)
        else:
            # 3+ channels (non-SAR models, future use)
            t1_tensor = torch.from_numpy(t1_arr).permute(2, 0, 1)

        if t2_channels == 1:
            t2_tensor = torch.from_numpy(np.stack([t2_arr, t2_arr], axis=0))
        elif t2_channels == 2:
            t2_tensor = torch.from_numpy(t2_arr).permute(2, 0, 1)
        else:
            t2_tensor = torch.from_numpy(t2_arr).permute(2, 0, 1)

        # Build a preview-friendly numpy array for visualization (grayscale -> pseudo-RGB)
        if t1_channels <= 2:
            ch0_t1 = t1_arr if t1_arr.ndim == 2 else t1_arr[:, :, 0]
            t1_np = np.stack([ch0_t1, ch0_t1, ch0_t1], axis=-1)
        else:
            t1_np = t1_arr

        if t2_channels <= 2:
            ch0_t2 = t2_arr if t2_arr.ndim == 2 else t2_arr[:, :, 0]
            t2_np = np.stack([ch0_t2, ch0_t2, ch0_t2], axis=-1)
        else:
            t2_np = t2_arr

        model_service = ModelService.get_instance()
        try:
            if model_name == "changeformer_v6":
                prob_map, binary_mask = model_service.predict_changeformer(
                    pil_t1, pil_t2
                )
            else:
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

        # Phase N4 & N5: Nemotron Multimodal Classification (with context)
        from src.api.services.vision_pipeline import orchestrate_vision_classification
        import logging
        logger = logging.getLogger(__name__)
        
        nemotron_interpretations = {}
        try:
            nemotron_interpretations = orchestrate_vision_classification(
                t1_np=t1_np,
                t2_np=t2_np,
                regions=regions
            )
        except Exception as e:
            logger.warning(f"Nemotron classification failed in upload: {e}")

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
            nemotron_interpretations=nemotron_interpretations,
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
        
        result = run_change_detection(
            t1_np=t1_np,
            t2_np=t2_np,
            model_name="snunet_cd_sar",
            threshold=threshold,
            min_region_area_px=min_region_area_px,
        )

        elapsed = round(time.perf_counter() - t0, 3)

        # Nemotron Multimodal Classification
        from src.api.services.vision_pipeline import orchestrate_vision_classification
        nemotron_interpretations = {}
        try:
            nemotron_interpretations = orchestrate_vision_classification(
                t1_np=t1_np,
                t2_np=t2_np,
                regions=result.regions
            )
        except Exception as e:
            logger.warning(f"Nemotron classification failed in change-detection: {e}")

        return ChangeDetectionResponse(
            status="success",
            model_used="snunet_cd_sar",
            threshold=threshold,
            total_pixels=result.total_pixels,
            changed_pixels=result.changed_pixels,
            change_percentage=result.change_percentage,
            total_changed_area_sq_km=result.total_changed_area_sq_km,
            num_change_clusters=result.num_change_clusters,
            regions=result.regions,
            t1_preview_base64=result.t1_preview_base64,
            t2_preview_base64=result.t2_preview_base64,
            t1_grayscale_base64=result.t1_grayscale_base64,
            t2_grayscale_base64=result.t2_grayscale_base64,
            t1_false_color_base64=result.t1_false_color_base64,
            t2_false_color_base64=result.t2_false_color_base64,
            change_mask_base64=result.change_mask_base64,
            confidence_heatmap_base64=result.confidence_heatmap_base64,
            overlay_base64=result.overlay_base64,
            change_boxes_base64=result.change_boxes_base64,
            nemotron_interpretations=nemotron_interpretations,
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


@router.get(
    "/{job_id}/detections.geojson",
    summary="Get job detections as canonical GeoJSON FeatureCollection",
)
def get_job_detections_geojson(job_id: int):
    """
    Returns valid GeoJSON representation of all detections for a specific job.
    """
    db.init_db()
    if db.SessionLocal is None:
        raise HTTPException(status_code=500, detail="Database is not configured")
    
    session: Session = db.SessionLocal()
    try:
        job = session.query(ChangeDetectionJob).get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        detections = session.query(Detection).filter(Detection.job_id == job_id).all()

        features = []
        for det in detections:
            if not det.geometry:
                continue
            props = dict(det.properties or {})
            
            # Canonical Phase 7 vector properties
            props["region_id"] = props.get("region_id")
            props["class"] = "change"
            props["confidence"] = props.get("mean_change_prob")
            props["area_sq_km"] = props.get("approx_area_sq_km")
            
            features.append({
                "type": "Feature",
                "geometry": det.geometry,
                "properties": props
            })
            
        return {
            "type": "FeatureCollection",
            "features": features
        }
    finally:
        session.close()


@router.post(
    "/timeseries-availability",
    response_model=dict,
    summary="Check Availability for Time-Series",
)
async def check_timeseries_availability(req: TimeSeriesRequest) -> dict:
    """
    Check Sentinel-1 SAR imagery availability for a date range without running inference.
    """
    try:
        from src.data_ingestion.sentinel_client import SentinelHubClient, CDSEAuthManager
        client = SentinelHubClient(CDSEAuthManager())
        scenes = client.fetch_all_scene_metadata(req.bbox.to_list(), req.date_range, req.max_scenes)
        return {
            "status": "success",
            "acquisitions_found": len(scenes),
            "scenes": scenes,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Availability check failed: {str(exc)}")


@router.post(
    "/timeseries",
    response_model=TimeSeriesResponse,
    summary="Run Time-Series Change Detection",
)
async def detect_timeseries_changes(req: TimeSeriesRequest) -> TimeSeriesResponse:
    """
    Fetches a time series of Sentinel-1 acquisitions and runs pairwise inference across the sequence.
    """
    t0 = time.perf_counter()
    try:
        if req.model_name not in ["snunet_cd_sar"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{req.model_name}' is not allowed or has no trained checkpoint."
            )

        db.init_db()
        if db.SessionLocal is None:
            raise HTTPException(status_code=500, detail="Database is not configured")
        
        # 1. Fetch all acquisitions and decode to tensors for oldest and latest
        selection, t1_dict, t2_dict, all_meta = fetch_sar_timeseries(
            bbox=req.bbox.to_list(),
            date_range=req.date_range,
            output_resolution=req.resolution,
            max_scenes=req.max_scenes,
        )
        
        # 2. Run pairwise inference ONLY for Oldest -> Latest
        from src.api.services.inference_service import run_change_detection
        inference_result = run_change_detection(
            t1_np=t1_dict["array"],
            t2_np=t2_dict["array"],
            model_name=req.model_name,
            threshold=req.threshold,
            min_region_area_px=req.min_region_area_px,
        )
        
        session: Session = db.SessionLocal()
        
        try:
            t1_scene = _get_or_create_scene(session, t1_dict["meta"])
            t2_scene = _get_or_create_scene(session, t2_dict["meta"])
                
            job = ChangeDetectionJob(
                scene_before_id=t1_scene.id,
                scene_after_id=t2_scene.id,
                model_version=req.model_name,
                status="success"
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            
            # Insert detections
            for region in inference_result.regions:
                props = {
                    "region_id": region.region_id,
                    "area_px": region.area_px,
                    "approx_area_sq_km": region.approx_area_sq_km,
                    "mean_change_prob": region.mean_change_prob,
                    "severity": region.severity,
                    "label": region.label,
                }
                if region.geo_bbox and region.geo_centroid:
                    min_lon, min_lat, max_lon, max_lat = region.geo_bbox
                    cx, cy = region.geo_centroid
                    
                    geom = {
                        "type": "Polygon",
                        "coordinates": [[
                            [min_lon, min_lat],
                            [max_lon, min_lat],
                            [max_lon, max_lat],
                            [min_lon, max_lat],
                            [min_lon, min_lat]
                        ]]
                    }
                    props["centroid"] = [cx, cy]
                    
                    det = Detection(
                        job_id=job.id,
                        geometry=geom,
                        properties=props
                    )
                    session.add(det)
            
            session.commit()
            
            # Phase N4 & N5: Nemotron Multimodal Classification (with context)
            from src.api.services.vision_pipeline import orchestrate_vision_classification
            import logging
            logger = logging.getLogger(__name__)
            
            nemotron_interpretations = {}
            try:
                nemotron_interpretations = orchestrate_vision_classification(
                    t1_np=t1_dict["array"],
                    t2_np=t2_dict["array"],
                    regions=inference_result.regions
                )
            except Exception as e:
                logger.warning(f"Nemotron classification failed: {e}")
            
            final_result = PairwiseChangeResult(
                t1_acquisition=TimeSeriesAcquisition(
                    scene_id=t1_dict["meta"]["scene_id"],
                    acquisition_date=t1_dict["meta"]["acquisition_date"]
                ),
                t2_acquisition=TimeSeriesAcquisition(
                    scene_id=t2_dict["meta"]["scene_id"],
                    acquisition_date=t2_dict["meta"]["acquisition_date"]
                ),
                job_id=job.id,
                change_percentage=inference_result.change_percentage,
                num_change_clusters=inference_result.num_change_clusters,
                total_changed_area_sq_km=inference_result.total_changed_area_sq_km,
                regions=inference_result.regions,
                t1_preview_base64=inference_result.t1_preview_base64,
                t2_preview_base64=inference_result.t2_preview_base64,
                change_mask_base64=inference_result.change_mask_base64,
                confidence_heatmap_base64=inference_result.confidence_heatmap_base64,
                overlay_base64=inference_result.overlay_base64,
                nemotron_interpretations=nemotron_interpretations,
            )
            
            all_acquisitions = [
                TimeSeriesAcquisition(
                    scene_id=m["scene_id"],
                    acquisition_date=m["acquisition_date"],
                    orbit_state=m.get("orbit_state"),
                    relative_orbit=m.get("relative_orbit"),
                    mode=m.get("mode"),
                    polarizations=m.get("polarizations")
                ) for m in all_meta
            ]
        finally:
            session.close()

        elapsed = round(time.perf_counter() - t0, 3)
        
        return TimeSeriesResponse(
            status="success",
            bbox=req.bbox.to_list(),
            date_range=req.date_range,
            acquisitions_found=len(all_meta),
            acquisitions_used=2,
            acquisition_dates=(t1_dict["meta"]["acquisition_date"], t2_dict["meta"]["acquisition_date"]),
            all_acquisitions=all_acquisitions,
            model_used=req.model_name,
            threshold=req.threshold,
            result=final_result,
            execution_time_sec=elapsed,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Time-Series change detection failed: {e}",
        )
