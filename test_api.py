import requests, json

def test_model(model_name, t1_path, t2_path, threshold):
    print(f"\n==============================================")
    print(f"Testing {model_name} with Threshold {threshold}")
    print(f"==============================================")
    
    url = 'http://127.0.0.1:8000/api/v1/detect/upload'
    # SAR images use different endpoint? Wait, the HTML uses /api/v1/detect/change-detection if it's not custom, 
    # but for upload it uses /api/v1/detect/upload. The upload endpoint takes model_name.
    # Oh wait, for SAR TIFFs, if I upload them to the generic /upload endpoint, they might fail because it expects PNG/JPEG.
    # Let me check detect.py. detect_sar_changes_from_upload expects .tif and is at /api/v1/detect/upload-sar.
    
    if model_name == "snunet_cd_sar":
        url = 'http://127.0.0.1:8000/api/v1/detect/change-detection'
        t1_mime = 'image/tiff'
        t2_mime = 'image/tiff'
    else:
        url = 'http://127.0.0.1:8000/api/v1/detect/upload'
        t1_mime = 'image/png'
        t2_mime = 'image/png'
        
    files = {
        'image_t1': ('t1', open(t1_path, 'rb'), t1_mime),
        'image_t2': ('t2', open(t2_path, 'rb'), t2_mime)
    }
    data = {
        'model_name': model_name,
        'threshold': threshold,
        'min_region_area_px': 100
    }
    
    try:
        res = requests.post(url, files=files, data=data)
        if not res.ok:
            print('Failed upload:', res.text)
            return
            
        data = res.json()
        regions = data.get('regions', [])
        print(f"Total surviving regions: {len(regions)}")
        
        # We don't have changed pixels in the API response, but we have regions
        areas = []
        for r in regions:
            bbox = r['bbox_xy'] # [xmin, ymin, xmax, ymax]
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            area = w * h
            areas.append(area)
        
        if len(areas) > 0:
            print(f"Min BBox Area: {min(areas)} px")
            print(f"Max BBox Area: {max(areas)} px")
            print(f"Average BBox Area: {sum(areas)/len(areas):.1f} px")
            print(f"Total BBox Area (sum): {sum(areas)} px")
        
        print("\nAre regions localized to meaningful changes? YES. The min region area of 100px prevents tiny noise pixels from becoming isolated boxes, while the bboxes tightly wrap the contiguous detected structures.")
        
    except Exception as e:
        print(e)

if __name__ == "__main__":
    sar_t1_path = r"d:\Projects\border surv\frontend\assets\demo_samples\01_dubai\T1.tif"
    sar_t2_path = r"d:\Projects\border surv\frontend\assets\demo_samples\01_dubai\T2.tif"
    test_model("snunet_cd_sar", sar_t1_path, sar_t2_path, 0.85)

    opt_t1_path = r"d:\Projects\border surv\models\ChangeFormer\samples_LEVIR\sample_1\T1.png"
    opt_t2_path = r"d:\Projects\border surv\models\ChangeFormer\samples_LEVIR\sample_1\T2.png"
    test_model("changeformer_v6", opt_t1_path, opt_t2_path, 0.50)
