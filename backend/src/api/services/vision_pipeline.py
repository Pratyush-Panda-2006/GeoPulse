"""
Phase N3 Integration: Nemotron Vision Input Pipeline
"""
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict
import numpy as np
import hashlib
import json

from src.api.schemas import ChangedRegion, NemotronInterpretation
from src.api.services.vision_crop import is_region_large_enough, extract_aligned_crop
from src.api.services.vision_encoder import sar_pair_to_rgb, build_side_by_side_image, encode_jpeg
from src.api.services.vision_classifier import VisionClassifierClient, parse_nemotron_response

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
