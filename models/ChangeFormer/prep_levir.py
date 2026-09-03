import os
import random
from PIL import Image
from tqdm import tqdm

RAW_DIR = r"D:\Projects\border surv\data\raw\LEVIR-CD"
OUT_DIR = r"D:\Projects\border surv\data\processed\LEVIR-CD-256"
CROP_SIZE = 256

def prep_data():
    if not os.path.exists(RAW_DIR):
        print(f"Error: {RAW_DIR} not found.")
        return

    # Create output directories
    for sub in ['A', 'B', 'label', 'list']:
        os.makedirs(os.path.join(OUT_DIR, sub), exist_ok=True)

    A_dir = os.path.join(RAW_DIR, 'A')
    B_dir = os.path.join(RAW_DIR, 'B')
    L_dir = os.path.join(RAW_DIR, 'label')

    # Get all images
    files = [f for f in os.listdir(A_dir) if f.endswith(('.png', '.tif'))]
    files.sort()
    
    print(f"Found {len(files)} files in LEVIR-CD raw directory.")
    
    all_patches = []
    
    for filename in tqdm(files, desc="Cropping LEVIR-CD"):
        img_a = Image.open(os.path.join(A_dir, filename)).convert('RGB')
        img_b = Image.open(os.path.join(B_dir, filename)).convert('RGB')
        img_l = Image.open(os.path.join(L_dir, filename)).convert('L')
        
        w, h = img_a.size
        
        # Crop into 256x256 patches
        patch_idx = 0
        for i in range(0, w, CROP_SIZE):
            for j in range(0, h, CROP_SIZE):
                box = (i, j, i + CROP_SIZE, j + CROP_SIZE)
                
                patch_a = img_a.crop(box)
                patch_b = img_b.crop(box)
                patch_l = img_l.crop(box)
                
                # Check if it's completely black/white? ChangeFormer uses all patches.
                # However, if label is 255 for change, we should ensure it remains 255.
                
                patch_name = f"{os.path.splitext(filename)[0]}_{patch_idx}.png"
                
                patch_a.save(os.path.join(OUT_DIR, 'A', patch_name))
                patch_b.save(os.path.join(OUT_DIR, 'B', patch_name))
                patch_l.save(os.path.join(OUT_DIR, 'label', patch_name))
                
                all_patches.append(patch_name)
                patch_idx += 1

    # Split into train/val/test
    # Typical split for LEVIR-CD is roughly 70% train, 10% val, 20% test
    # Actually, official LEVIR has a predefined split (445 train, 64 val, 128 test images)
    # Let's group by original image to prevent data leakage!
    
    random.seed(42)
    random.shuffle(files)
    
    num_files = len(files)
    train_end = int(num_files * 0.7)
    val_end = int(num_files * 0.8)
    
    train_files = files[:train_end]
    val_files = files[train_end:val_end]
    test_files = files[val_end:]
    
    def write_list(split_name, source_files):
        split_patches = []
        for filename in source_files:
            base = os.path.splitext(filename)[0]
            for idx in range(16): # 1024x1024 / 256x256 = 16 patches
                split_patches.append(f"{base}_{idx}.png")
        
        with open(os.path.join(OUT_DIR, 'list', f"{split_name}.txt"), 'w') as f:
            for p in split_patches:
                f.write(f"{p}\n")
        print(f"Wrote {len(split_patches)} patches to {split_name}.txt")

    write_list('train', train_files)
    write_list('val', val_files)
    write_list('test', test_files)
    
    print("Preprocessing completed successfully.")

if __name__ == "__main__":
    prep_data()
