import os
import shutil

source_dir = r"d:\Projects\border surv\data\raw\LEVIR-CD"
dest_dir = r"d:\Projects\border surv\models\ChangeFormer\samples_LEVIR"

samples = [
    "test_45.png",
    "train_189.png",
    "test_20.png",
    "val_20.png",
    "train_231.png"
]

os.makedirs(dest_dir, exist_ok=True)

for i, sample in enumerate(samples, 1):
    sample_dir = os.path.join(dest_dir, f"sample_{i}")
    os.makedirs(sample_dir, exist_ok=True)
    
    # Copy A to T1
    shutil.copy2(os.path.join(source_dir, "A", sample), os.path.join(sample_dir, "T1.png"))
    # Copy B to T2
    shutil.copy2(os.path.join(source_dir, "B", sample), os.path.join(sample_dir, "T2.png"))
    # Copy label to label.png
    shutil.copy2(os.path.join(source_dir, "label", sample), os.path.join(sample_dir, "label.png"))
    
    print(f"Sample {i} created from {sample}")
