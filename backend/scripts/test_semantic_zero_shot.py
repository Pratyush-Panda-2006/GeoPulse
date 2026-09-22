import os
import sys
import time
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from dotenv import load_dotenv

# Ensure backend directory is in path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.api import db
from src.api.models import SARSceneAsset, SARScene
from src.storage.object_storage import download_bytes
from src.preprocessing.sar_loader import load_sar_pair_for_inference, extract_geotiff_metadata
from src.api.services.inference_service import run_change_detection
from src.api.services.visualization import sar_dualpol_to_rgb
from src.api.services.archive_retrieval_encoder import ArchiveRetrievalEncoder
import open_clip

def main():
    load_dotenv()
    
    # 1. Load the existing RemoteCLIP model
    checkpoint_path = os.getenv("ARCHIVE_RETRIEVAL_MODEL_PATH")
    if not checkpoint_path:
        print("Error: ARCHIVE_RETRIEVAL_MODEL_PATH not set in .env")
        return
        
    print(f"Loading RemoteCLIP from {checkpoint_path}...")
    encoder = ArchiveRetrievalEncoder(checkpoint_path)
    
    # 2. Load the existing Asset 1 and Asset 2 SAR data
    db.init_db()
    session = db.SessionLocal()
    
    before_asset_id = 1
    after_asset_id = 2
    
    try:
        before_asset = session.query(SARSceneAsset).get(before_asset_id)
        after_asset = session.query(SARSceneAsset).get(after_asset_id)
        
        if not before_asset or not after_asset:
            print(f"Error: Could not find assets {before_asset_id} and {after_asset_id}")
            return
            
        print(f"Loaded Asset 1 (ID: {before_asset.id}) and Asset 2 (ID: {after_asset.id})")
        
        before_bytes = download_bytes(before_asset.storage_key)
        after_bytes = download_bytes(after_asset.storage_key)
        
        after_geo_meta = extract_geotiff_metadata(after_bytes)
        transform = after_geo_meta.get("transform")
        crs = after_geo_meta.get("crs")
        
        print("Decoding GeoTIFFs...")
        t1_np, t2_np = load_sar_pair_for_inference(
            before_bytes,
            after_bytes,
            is_linear=True,
            return_tensors=False,
        )
        
        # 3. Reproduce Model 3 change detection
        print("Running Model 3 change detection...")
        result = run_change_detection(
            t1_np=t1_np,
            t2_np=t2_np,
            model_name="snunet_cd_sar",
            threshold=0.5,
            min_region_area_px=100,
            bbox=[
                after_asset.bbox_min_lon,
                after_asset.bbox_min_lat,
                after_asset.bbox_max_lon,
                after_asset.bbox_max_lat,
            ],
            transform=transform,
            crs=crs,
        )
        
        print(f"Detected {len(result.regions)} change regions.")
        
        # 6. Create text embeddings for classes
        classes = {
            "construction": [
                "new construction and buildings",
                "newly built structures",
                "construction and built-up expansion",
            ],
            "clearance": [
                "demolition and cleared structures",
                "cleared land after demolition",
                "removal of buildings",
            ],
            "water": [
                "water extent change",
                "flooded or newly inundated area",
                "change in water bodies",
            ],
            "road": [
                "new roads and infrastructure",
                "road construction",
                "transportation infrastructure change",
            ],
            "vegetation": [
                "vegetation or land-cover change",
                "vegetation clearing",
                "changes in vegetation",
            ],
            "other": [
                "other land surface change",
                "miscellaneous environmental or structural change",
                "other satellite-detected change",
            ]
        }
        
        templates = [
            "A satellite SAR image showing {}",
            "An overhead remote sensing image showing {}",
            "A satellite image of {}",
            "Aerial imagery showing {}",
        ]
        
        class_embeddings = {}
        class_names = list(classes.keys())
        
        print("Encoding text classes...")
        for class_name, descriptions in classes.items():
            all_prompts = []
            for desc in descriptions:
                for tpl in templates:
                    all_prompts.append(tpl.format(desc))
                    
            tokens = open_clip.tokenize(all_prompts).to(encoder.device)
            with torch.no_grad():
                emb = encoder.model.encode_text(tokens)
                # average across all prompts for this class
                emb = emb.mean(dim=0, keepdim=True)
                emb = emb / emb.norm(dim=-1, keepdim=True)
                class_embeddings[class_name] = emb.cpu().numpy().astype(np.float32).flatten()
                
        # 4 & 5. Extract and encode every region
        print("\\nStarting zero-shot semantic classification...\\n")
        
        results_summary = []
        
        for region in result.regions:
            # Depending on how ChangedRegion is implemented, it might be a dict or object
            if isinstance(region, dict):
                rid = region.get("region_id", "")
                area = region.get("area_px", 0)
                bbox = region.get("bbox_xy", [0, 0, 0, 0])
            else:
                rid = getattr(region, "region_id", "")
                area = getattr(region, "area_px", 0)
                bbox = getattr(region, "bbox_xy", [0, 0, 0, 0])
                
            min_row, min_col, max_row, max_col = [int(x) for x in bbox]
            
            # Crop AFTER SAR array
            t2_crop = t2_np[:, min_row:max_row, min_col:max_col]
            
            # Skip invalid crops
            if t2_crop.size == 0 or t2_crop.shape[1] == 0 or t2_crop.shape[2] == 0:
                continue
                
            # Convert using existing sar_dualpol_to_rgb
            rgb_crop = sar_dualpol_to_rgb(t2_crop)
            image = Image.fromarray(rgb_crop)
            
            # Encode image
            image_tensor = encoder.preprocess(image)
            with torch.no_grad():
                tensor = image_tensor.unsqueeze(0).to(encoder.device)
                img_emb = encoder.model.encode_image(tensor)
                img_emb = img_emb / img_emb.norm(dim=-1, keepdim=True)
                img_emb_np = img_emb.cpu().numpy().astype(np.float32).flatten()
                
            # Score against classes
            scores = {}
            for class_name, txt_emb in class_embeddings.items():
                # dot product of L2-normalized vectors = cosine similarity
                score = np.dot(img_emb_np, txt_emb)
                scores[class_name] = float(score)
                
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            top_class, top_score = sorted_scores[0]
            second_class, second_score = sorted_scores[1]
            margin = top_score - second_score
            
            # Print table
            print(f"Region A{rid}")
            print(f"Area: {area}")
            print(f"BBox: {bbox}")
            print()
            for cls_name in class_names:
                print(f"{cls_name:<15} {scores[cls_name]:.4f}")
            print()
            print(f"TOP: {top_class}")
            print(f"Raw top-3: {sorted_scores[:3]}")
            print("-" * 40)
            
            results_summary.append({
                "region_id": f"A{rid}",
                "top_class": top_class,
                "top_score": top_score,
                "second_class": second_class,
                "second_score": second_score,
                "margin": margin,
            })
            
        # Print summary
        print("\\n===== ZERO-SHOT SUMMARY =====")
        print("For each region:")
        print("region_id | top_class | top_score | second_class | second_score | margin")
        for res in results_summary:
            print(f"{res['region_id']:<9} | {res['top_class']:<15} | {res['top_score']:.4f} | {res['second_class']:<15} | {res['second_score']:.4f} | {res['margin']:.4f}")
            
        print("\\nAmbiguous regions specifically:")
        for res in results_summary:
            if res['region_id'] in ["A2", "A4", "A10"]:
                print(f"{res['region_id']:<9} | {res['top_class']:<15} | {res['top_score']:.4f} | {res['second_class']:<15} | {res['second_score']:.4f} | {res['margin']:.4f}")
                
    finally:
        session.close()

if __name__ == "__main__":
    main()
