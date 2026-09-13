import io
import json
import base64
import os
import sys

from fastapi.testclient import TestClient
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.api.main import app

client = TestClient(app)

def run_real_tests():
    print("--- REAL END-TO-END DEMO ---")
    t1_path = r"d:\Projects\border surv\models\ChangeFormer\samples_LEVIR\sample_1\T1.png"
    t2_path = r"d:\Projects\border surv\models\ChangeFormer\samples_LEVIR\sample_1\T2.png"
    
    with open(t1_path, "rb") as f1, open(t2_path, "rb") as f2:
        t1_bytes = f1.read()
        t2_bytes = f2.read()

    print(f"Loaded T1 ({len(t1_bytes)} bytes) and T2 ({len(t2_bytes)} bytes).")
    print("\n1. Running ChangeFormerV6 Inference (POST /api/v1/detect/upload) ... this may take a minute on CPU.")
    
    resp_rgb = client.post(
        "/api/v1/detect/upload",
        files={
            "image_t1": ("t1.png", t1_bytes, "image/png"),
            "image_t2": ("t2.png", t2_bytes, "image/png")
        },
        data={"model_name": "changeformer_v6", "threshold": 0.5, "min_region_area_px": 5}
    )
    
    if resp_rgb.status_code != 200:
        print("FAILED RGB Inference:", resp_rgb.status_code, resp_rgb.text)
        return
    else:
        print("SUCCESS RGB Inference:", resp_rgb.status_code)
        
    data = resp_rgb.json()
    regions = data.get("regions", [])
    print(f"Detected {len(regions)} regions.")
    
    if not regions:
        print("No regions detected. Cannot test Omni.")
        return
        
    print("\n2. Filtering high-confidence regions (prob >= 0.7) ...")
    high_conf_regions = [r for r in regions if r["mean_change_prob"] >= 0.7]
    print(f"Found {len(high_conf_regions)} high-confidence regions.")
    
    if not high_conf_regions:
        print("No high-confidence regions. Taking top 3 regions instead.")
        high_conf_regions = sorted(regions, key=lambda x: x["mean_change_prob"], reverse=True)[:3]
    
    payload = {
        "t1_base64": data.get("t1_preview_base64", ""),
        "t2_base64": data.get("t2_preview_base64", ""),
        "regions": high_conf_regions
    }
    
    print("\n3. Requesting Semantic Interpretation (POST /api/v1/detect/interpret) ...")
    resp_omni = client.post(
        "/api/v1/detect/interpret",
        json=payload
    )
    
    if resp_omni.status_code != 200:
        print("FAILED Omni:", resp_omni.status_code, resp_omni.text)
        return
        
    print("SUCCESS Omni:", resp_omni.status_code)
    
    omni_data = resp_omni.json()
    interpretations = omni_data.get("interpretations", {})
    
    for r in high_conf_regions:
        rid = str(r["region_id"])
        print(f"\n--- REGION {rid} ---")
        print(f"BBox: {r['bbox_xy']}")
        print(f"Probability: {r['mean_change_prob']:.4f}")
        interp = interpretations.get(rid, {})
        if not interp:
            print("No interpretation returned.")
        else:
            status = interp.get("status")
            print(f"Status: {status}")
            if status == "skipped_small_crop":
                print("Crop was too small to interpret.")
            elif status in ("error", "unavailable", "malformed_response"):
                print("Error:", interp.get("error"))
            else:
                print("Category:", interp.get("category"))
                print("Visual Confidence:", interp.get("visual_confidence"))
                print("Visual Cues:", interp.get("visual_cues"))
                print("Short Summary:", interp.get("short_summary"))
                print("Uncertainty:", interp.get("uncertainty"))

if __name__ == "__main__":
    run_real_tests()
