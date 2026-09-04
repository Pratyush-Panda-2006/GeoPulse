"""
Phase N3 Integration: Nemotron Vision Input Pipeline
"""
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict
import numpy as np
import hashlib
import json

from src.api.schemas import ChangedRegion, NemotronInterpretation
from src.api.services.vision_crop import is_region_large_enough, extract_aligned_crop, VisionCrop
from src.api.services.vision_encoder import sar_pair_to_rgb, build_side_by_side_image, encode_jpeg
from src.api.services.vision_classifier import VisionClassifierClient, parse_nemotron_response
import base64
import io
from PIL import Image, ImageDraw

@dataclass
class NemotronPayload:
    status: str
    jpeg_bytes: Optional[bytes] = None
    crop_bbox: Optional[Tuple[int, int, int, int]] = None

def prepare_vision_payload(
    t1_np: np.ndarray,
    t2_np: np.ndarray,
    region: ChangedRegion
) -> NemotronPayload:
    """
    Evaluates a detected region and prepares the Nemotron vision payload if eligible.
    
    Rules:
    - Only HIGH-severity regions.
    - Only regions large enough.
    - Synchronized extraction, RGB conversion, and JPEG encoding.
    """
    if region.severity.lower() != "high":
        return NemotronPayload(status="skipped_non_high")
        
    if not is_region_large_enough(region.bbox_xy):
        return NemotronPayload(status="skipped_small_crop")
        
    # 5. Use extract_aligned_crop() for padded T1/T2 extraction
    crop = extract_aligned_crop(t1_np, t2_np, region.bbox_xy, padding_px=32)
    
    # 6. Use vision_encoder.py to convert synchronized crops into RGB
    t1_rgb, t2_rgb = sar_pair_to_rgb(crop.t1, crop.t2)
    
    # Build side-by-side
    combined = build_side_by_side_image(t1_rgb, t2_rgb)
    
    # Encode as JPEG
    jpeg_bytes = encode_jpeg(combined, quality=90)
    
    return NemotronPayload(
        status="ready",
        jpeg_bytes=jpeg_bytes,
        crop_bbox=crop.bbox
    )


def compute_cache_key(
    jpeg_bytes: bytes,
    bbox: Tuple[int, int, int, int],
    prompt: str,
    model_name: str,
    pipeline_version: str = "v1"
) -> str:
    h = hashlib.sha256()
    h.update(jpeg_bytes)
    h.update(str(bbox).encode('utf-8'))
    h.update(model_name.encode('utf-8'))
    h.update(prompt.encode('utf-8'))
    h.update(pipeline_version.encode('utf-8'))
    return h.hexdigest()


def orchestrate_vision_classification(
    t1_np: np.ndarray,
    t2_np: np.ndarray,
    regions: List[ChangedRegion]
) -> Dict[int, NemotronInterpretation]:
    """
    Orchestrates the N4 Nemotron integration for a list of detected regions.
    Enforces a hard ceiling of max 3 API calls per analysis.
    """
    interpretations = {}
    calls_made = 0
    max_calls = 3
    
    client = VisionClassifierClient()
    
    for region in regions:
        payload = prepare_vision_payload(t1_np, t2_np, region)
        
        if payload.status != "ready":
            interpretations[region.region_id] = NemotronInterpretation(
                region_id=region.region_id,
                status=payload.status
            )
            continue
            
        if calls_made >= max_calls:
            interpretations[region.region_id] = NemotronInterpretation(
                region_id=region.region_id,
                status="call_limit_reached"
            )
            continue
            
        prompt = (
            "Model 3 has already detected a high-severity change in this region.\n"
            "Your task is to classify the TYPE of the detected change using the attached T1/BEFORE (left) and T2/AFTER (right) image.\n"
            "Select the most plausible category supported by the visual evidence.\n"
            "Do not rediscover whether change exists—assume it does.\n"
            "Do not claim causal proof, and do not use unsupported legality, intent, or ownership claims.\n"
        )

        if getattr(region, "evidence", None):
            evidence_dict = region.evidence.dict(exclude_none=True)
            if evidence_dict:
                prompt += (
                    "\n--- CONTEXTUAL EVIDENCE ---\n"
                    "The following environmental/geospatial context is provided for this region:\n"
                    f"{evidence_dict}\n"
                    "RULES FOR CONTEXT:\n"
                    "- Use this ONLY as SUPPORTING context.\n"
                    "- Never override Model 3 detection or probability based on this context.\n"
                    "- Never force a category strictly from context; visual evidence remains primary.\n"
                    "- Use context to explain uncertainty or increase/decrease your interpretation confidence.\n"
                )

        prompt += "\nReturn the strict JSON format specified in the system prompt only."
        
        # Check Cache
        cache_key = compute_cache_key(
            jpeg_bytes=payload.jpeg_bytes,
            bbox=payload.crop_bbox,
            prompt=prompt,
            model_name=client.model
        )
        
        from src.api.db import SessionLocal
        from src.api.models.nemotron_cache import NemotronCache
        
        db = SessionLocal() if SessionLocal else None
        cached_hit = False
        if db:
            try:
                cached = db.query(NemotronCache).filter(NemotronCache.cache_key == cache_key).first()
                if cached:
                    interpretations[region.region_id] = NemotronInterpretation(
                        region_id=region.region_id,
                        status="classified",
                        category=cached.category,
                        visual_confidence=cached.visual_confidence,
                        short_summary=cached.short_summary,
                        visual_cues=json.loads(cached.visual_cues) if cached.visual_cues else None,
                        uncertainty=cached.uncertainty
                    )
                    cached_hit = True
            except Exception:
                pass
            finally:
                db.close()
                
        if cached_hit:
            continue
            
        if calls_made >= max_calls:
            interpretations[region.region_id] = NemotronInterpretation(
                region_id=region.region_id,
                status="call_limit_reached"
            )
            continue
            
        calls_made += 1

        try:
            raw_response = client.classify_image_bytes(payload.jpeg_bytes, prompt, max_retries_override=1)
            
            try:
                parsed = parse_nemotron_response(raw_response)
                
                if db:
                    db = SessionLocal()
                    try:
                        new_cache = NemotronCache(
                            cache_key=cache_key,
                            category=parsed.category,
                            visual_confidence=parsed.visual_confidence,
                            short_summary=parsed.short_summary,
                            visual_cues=json.dumps(parsed.visual_cues) if parsed.visual_cues else None,
                            uncertainty=parsed.uncertainty
                        )
                        db.add(new_cache)
                        db.commit()
                    except Exception:
                        db.rollback()
                    finally:
                        db.close()

                interpretations[region.region_id] = NemotronInterpretation(
                    region_id=region.region_id,
                    status="classified",
                    category=parsed.category,
                    visual_confidence=parsed.visual_confidence,
                    short_summary=parsed.short_summary,
                    visual_cues=parsed.visual_cues,
                    uncertainty=parsed.uncertainty
                )
            except Exception as e:
                interpretations[region.region_id] = NemotronInterpretation(
                    region_id=region.region_id,
                    status="malformed_response",
                    error=str(e)
                )
        except Exception as e:
            interpretations[region.region_id] = NemotronInterpretation(
                region_id=region.region_id,
                status="unavailable",
                error=str(e)
            )
            
    return interpretations


def orchestrate_vision_classification_from_rgb(
    t1_b64: str,
    t2_b64: str,
    regions: List[ChangedRegion]
) -> Dict[int, NemotronInterpretation]:
    """
    Decoupled Omni interpretation using base64 RGB previews.
    Takes T1 and T2 base64 RGB images, extracts padded crops,
    creates a 3-panel side-by-side image (T1 crop | T2 crop | T2 crop with bbox),
    and queries Nemotron.
    """
    interpretations = {}
    
    # Strip data URL prefix if present
    if t1_b64.startswith("data:image"):
        t1_b64 = t1_b64.split(",")[1]
    if t2_b64.startswith("data:image"):
        t2_b64 = t2_b64.split(",")[1]
        
    t1_bytes = base64.b64decode(t1_b64)
    t2_bytes = base64.b64decode(t2_b64)
    
    t1_pil = Image.open(io.BytesIO(t1_bytes)).convert("RGB")
    t2_pil = Image.open(io.BytesIO(t2_bytes)).convert("RGB")
    
    t1_np = np.array(t1_pil)
    t2_np = np.array(t2_pil)
    
    # extract_aligned_crop expects (C, H, W)
    t1_chw = np.transpose(t1_np, (2, 0, 1))
    t2_chw = np.transpose(t2_np, (2, 0, 1))
    
    client = VisionClassifierClient()
    
    for region in regions:
        # P0 constraint: Omni only processes high confidence regions
        # Check severity or probability. Let's use severity == "High" or "Critical"
        # However, the user said "select qualifying high-confidence regions", so we'll 
        # interpret what is given in `regions` (the filtering can happen before or here).
        
        # Check if region is large enough
        if not is_region_large_enough(region.bbox_xy):
            interpretations[region.region_id] = NemotronInterpretation(
                region_id=region.region_id,
                status="skipped_small_crop"
            )
            continue
            
        crop = extract_aligned_crop(t1_chw, t2_chw, region.bbox_xy, padding_px=32)
        
        # Convert back to (H, W, 3)
        t1_crop_rgb = np.transpose(crop.t1, (1, 2, 0)).astype(np.uint8)
        t2_crop_rgb = np.transpose(crop.t2, (1, 2, 0)).astype(np.uint8)
        
        # Third panel: T2 with Bounding Box of the change
        # The region's original bbox was (min_row, min_col, max_row, max_col)
        # The crop's bbox is crop.bbox = (padded_min_row, padded_min_col, padded_max_row, padded_max_col)
        # So the bounding box in the crop's local coordinates is:
        min_row, min_col, max_row, max_col = region.bbox_xy
        pad_min_row, pad_min_col, _, _ = crop.bbox
        
        local_min_row = min_row - pad_min_row
        local_min_col = min_col - pad_min_col
        local_max_row = max_row - pad_min_row
        local_max_col = max_col - pad_min_col
        
        t2_box_pil = Image.fromarray(t2_crop_rgb).copy()
        draw = ImageDraw.Draw(t2_box_pil)
        # Bbox for PIL is [x0, y0, x1, y1] -> [col, row, col, row]
        draw.rectangle(
            [local_min_col, local_min_row, local_max_col, local_max_row],
            outline="#ffb000",
            width=max(2, int(t2_box_pil.width / 50))
        )
        t2_box_rgb = np.array(t2_box_pil)
        
        # Concatenate 3 panels side-by-side
        combined = np.concatenate([t1_crop_rgb, t2_crop_rgb, t2_box_rgb], axis=1).astype(np.uint8, copy=False)
        jpeg_bytes = encode_jpeg(combined, quality=90)
        
        prompt = (
            "A high-severity change has been detected in this region.\n"
            "Your task is to classify the TYPE of the detected change using the attached 3-panel image:\n"
            "Panel 1 (left): T1/BEFORE\n"
            "Panel 2 (middle): T2/AFTER\n"
            "Panel 3 (right): T2/AFTER with the bounding box highlighting the exact change region.\n"
            "Select the most plausible category supported by the visual evidence.\n"
            "If the change cannot be reliably determined from the visual evidence, return 'uncertain'. Do not hallucinate.\n"
            "Do not rediscover whether change exists—assume it does.\n"
            "Do not claim causal proof, and do not use unsupported legality, intent, or ownership claims.\n"
        )

        if getattr(region, "evidence", None):
            evidence_dict = region.evidence.dict(exclude_none=True)
            if evidence_dict:
                prompt += (
                    "\n--- CONTEXTUAL EVIDENCE ---\n"
                    "The following environmental/geospatial context is provided for this region:\n"
                    f"{evidence_dict}\n"
                    "RULES FOR CONTEXT:\n"
                    "- Use this ONLY as SUPPORTING context.\n"
                    "- Never override the visual evidence.\n"
                    "- Never force a category strictly from context; visual evidence remains primary.\n"
                    "- Use context to explain uncertainty or increase/decrease your interpretation confidence.\n"
                )

        prompt += "\nReturn the strict JSON format specified in the system prompt only."
        
        # Check Cache
        cache_key = compute_cache_key(
            jpeg_bytes=jpeg_bytes,
            bbox=crop.bbox,
            prompt=prompt,
            model_name=client.model
        )
        
        from src.api.db import SessionLocal
        from src.api.models.nemotron_cache import NemotronCache
        
        db = SessionLocal() if SessionLocal else None
        cached_hit = False
        if db:
            try:
                cached = db.query(NemotronCache).filter(NemotronCache.cache_key == cache_key).first()
                if cached:
                    interpretations[region.region_id] = NemotronInterpretation(
                        region_id=region.region_id,
                        status="classified",
                        category=cached.category,
                        visual_confidence=cached.visual_confidence,
                        short_summary=cached.short_summary,
                        visual_cues=json.loads(cached.visual_cues) if cached.visual_cues else None,
                        uncertainty=cached.uncertainty
                    )
                    cached_hit = True
            except Exception:
                pass
            finally:
                db.close()
                
        if cached_hit:
            continue
            
        try:
            raw_response = client.classify_image_bytes(jpeg_bytes, prompt, max_retries_override=1)
            
            try:
                parsed = parse_nemotron_response(raw_response)
                
                if db:
                    db = SessionLocal()
                    try:
                        new_cache = NemotronCache(
                            cache_key=cache_key,
                            category=parsed.category,
                            visual_confidence=parsed.visual_confidence,
                            short_summary=parsed.short_summary,
                            visual_cues=json.dumps(parsed.visual_cues) if parsed.visual_cues else None,
                            uncertainty=parsed.uncertainty
                        )
                        db.add(new_cache)
                        db.commit()
                    except Exception:
                        db.rollback()
                    finally:
                        db.close()

                interpretations[region.region_id] = NemotronInterpretation(
                    region_id=region.region_id,
                    status="classified",
                    category=parsed.category,
                    visual_confidence=parsed.visual_confidence,
                    short_summary=parsed.short_summary,
                    visual_cues=parsed.visual_cues,
                    uncertainty=parsed.uncertainty
                )
            except Exception as e:
                interpretations[region.region_id] = NemotronInterpretation(
                    region_id=region.region_id,
                    status="malformed_response",
                    error=str(e)
                )
        except Exception as e:
            interpretations[region.region_id] = NemotronInterpretation(
                region_id=region.region_id,
                status="unavailable",
                error=str(e)
            )
            
    return interpretations
