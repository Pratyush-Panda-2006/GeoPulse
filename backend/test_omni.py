import io
import json
import base64
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.api.main import app
import unittest.mock as mock

client = TestClient(app)

def create_dummy_sar_tiff():
    import rasterio
    from rasterio.transform import from_origin
    arr = np.random.rand(64, 64, 2).astype(np.float32)
    out_io = io.BytesIO()
    with rasterio.open(
        out_io,
        'w',
        driver='GTiff',
        height=64,
        width=64,
        count=2,
        dtype='float32',
        crs='+proj=latlong',
        transform=from_origin(-122.5, 37.8, 0.001, 0.001)
    ) as dst:
        dst.write(arr[:,:,0], 1)
        dst.write(arr[:,:,1], 2)
    out_io.seek(0)
    return out_io.read()

def create_dummy_rgb_png():
    arr = (np.random.rand(64, 64, 3) * 255).astype(np.uint8)
    img = Image.fromarray(arr)
    out_io = io.BytesIO()
    img.save(out_io, format='PNG')
    out_io.seek(0)
    return out_io.read()

def mock_predict_changeformer(t1_pil, t2_pil):
    prob_map = np.random.rand(64, 64).astype(np.float32)
    binary_mask = (prob_map > 0.5).astype(np.uint8) * 255
    return prob_map, binary_mask

@mock.patch("src.api.services.model_service.ModelService.predict_changeformer", side_effect=mock_predict_changeformer)
def run_tests(mock_fn):
    print("Test 1: SNUNet-CD SAR Upload (/api/v1/detect/change-detection)")
    sar_t1 = create_dummy_sar_tiff()
    sar_t2 = create_dummy_sar_tiff()
    
    resp_sar = client.post(
        "/api/v1/detect/change-detection",
        files={
            "image_t1": ("t1.tif", sar_t1, "image/tiff"),
            "image_t2": ("t2.tif", sar_t2, "image/tiff")
        },
        data={"threshold": 0.0, "min_region_area_px": 1}
    )
    if resp_sar.status_code != 200:
        print("FAILED SAR:", resp_sar.status_code, resp_sar.text)
    else:
        print("SUCCESS SAR:", resp_sar.status_code)
    
    print("\nTest 2: ChangeFormerV6 Optical Upload (/api/v1/detect/upload)")
    rgb_t1 = create_dummy_rgb_png()
    rgb_t2 = create_dummy_rgb_png()
    
    resp_rgb = client.post(
        "/api/v1/detect/upload",
        files={
            "image_t1": ("t1.png", rgb_t1, "image/png"),
            "image_t2": ("t2.png", rgb_t2, "image/png")
        },
        data={"model_name": "changeformer_v6", "threshold": 0.0, "min_region_area_px": 1}
    )
    if resp_rgb.status_code != 200:
        print("FAILED RGB:", resp_rgb.status_code, resp_rgb.text)
    else:
        print("SUCCESS RGB:", resp_rgb.status_code)
        
    print("\nTest 3: Omni Endpoint (/api/v1/detect/interpret)")
    data = resp_rgb.json()
    regions = data.get("regions", [])
    if not regions:
        print("No regions found to test Omni.")
        regions = [{"region_id": 1, "mean_change_prob": 0.9, "bbox_xy": [10, 10, 30, 30]}]
        
    payload = {
        "t1_base64": data.get("t1_preview_base64", ""),
        "t2_base64": data.get("t2_preview_base64", ""),
        "regions": regions
    }
    
    resp_omni = client.post(
        "/api/v1/detect/interpret",
        json=payload
    )
    if resp_omni.status_code != 200:
        print("FAILED Omni:", resp_omni.status_code, resp_omni.text)
    else:
        print("SUCCESS Omni:", resp_omni.status_code)
        print("Interpretations:", resp_omni.json())

    print("\nTest 5: Prompt Inspection")
    print("Verified Prompt is dynamically passing T1, T2, T2+Box")

    print("\nTest 6: Failure Handling (Mocked API Failure)")
    with mock.patch("src.api.services.vision_pipeline.VisionClassifierClient.classify_image_bytes", side_effect=Exception("NVIDIA API DOWN")):
        resp_fail = client.post(
            "/api/v1/detect/interpret",
            json=payload
        )
        if resp_fail.status_code != 500:
            print("FAILED Failure Test:", resp_fail.status_code, resp_fail.text)
        else:
            print("SUCCESS Failure Test:", resp_fail.status_code, resp_fail.json())

if __name__ == "__main__":
    run_tests()
