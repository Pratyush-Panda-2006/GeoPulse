import sys
from pathlib import Path
import numpy as np
import torch
from PIL import Image
import os

# Add backend to sys.path
sys.path.append(os.path.abspath("."))

from src.api.services.model_service import ModelService
from src.api.services.change_analyzer import extract_changed_regions
from src.preprocessing.sar_loader import load_sar_pair_for_inference

def get_sar_tensors(t1_path, t2_path):
    with open(t1_path, 'rb') as f1, open(t2_path, 'rb') as f2:
        t1_bytes = f1.read()
        t2_bytes = f2.read()
    
    t1_np, t2_np = load_sar_pair_for_inference(
        t1_bytes, t2_bytes, is_linear=False, return_tensors=False
    )
    t1_np = t1_np[:, :512, :512]
    t2_np = t2_np[:, :512, :512]
    t1_tensor = torch.from_numpy(t1_np)
    t2_tensor = torch.from_numpy(t2_np)
    return t1_tensor, t2_tensor

def get_optical_images(t1_path, t2_path):
    t1_img = Image.open(t1_path).convert('RGB')
    t2_img = Image.open(t2_path).convert('RGB')
    return t1_img, t2_img

def compute_stats(name, prob_map):
    print(f"=== {name} ===")
    print(f"Min: {np.min(prob_map):.4f}")
    print(f"Max: {np.max(prob_map):.4f}")
    print(f"Mean: {np.mean(prob_map):.4f}")
    for p in [90, 95, 97, 99]:
        print(f"P{p}: {np.percentile(prob_map, p):.4f}")
    print()

def eval_thresholds(name, prob_map):
    thresholds = [0.5, 0.7, 0.8, 0.85, 0.9, 0.95]
    areas = [10, 50, 100]
    print(f"--- Sweeping {name} ---")
    for th in thresholds:
        bmask = (prob_map >= th).astype(np.uint8)
        px_count = np.sum(bmask)
        print(f"Threshold {th}: {px_count} pixels surviving")
        for area in areas:
            regions, _ = extract_changed_regions(bmask, prob_map, min_region_area_px=area)
            print(f"  Area {area}px: {len(regions)} regions")
    print()

if __name__ == "__main__":
    ms = ModelService.get_instance()
    
    # 1. SAR Demo (Dubai)
    sar_t1_path = r"..\frontend\assets\demo_samples\01_dubai\T1.tif"
    sar_t2_path = r"..\frontend\assets\demo_samples\01_dubai\T2.tif"
    
    if not os.path.exists(sar_t1_path):
        sar_t1_path = r"..\Frontend\assets\demo_samples\01_dubai\t1.tif"
        sar_t2_path = r"..\Frontend\assets\demo_samples\01_dubai\t2.tif"
        
    t1_t, t2_t = get_sar_tensors(sar_t1_path, sar_t2_path)
    prob_map_sar, _ = ms.predict_change_rgb(t1_t, t2_t, model_name="snunet_cd_sar")
    
    compute_stats("SNUNet-CD (SAR)", prob_map_sar)
    eval_thresholds("SNUNet-CD (SAR)", prob_map_sar)
    
    # 2. Optical Demo (LEVIR)
    opt_t1_path = r"..\models\ChangeFormer\samples_LEVIR\sample_1\T1.png"
    opt_t2_path = r"..\models\ChangeFormer\samples_LEVIR\sample_1\T2.png"
    
    t1_img, t2_img = get_optical_images(opt_t1_path, opt_t2_path)
    prob_map_opt, _ = ms.predict_changeformer(t1_img, t2_img)
    
    compute_stats("ChangeFormerV6 (Optical)", prob_map_opt)
    eval_thresholds("ChangeFormerV6 (Optical)", prob_map_opt)
