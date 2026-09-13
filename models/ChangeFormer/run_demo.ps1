# Pre-requisite: You need to download the pretrained weights for ChangeFormer.
# 1. Download pretrained_changeformer.pt from the official repo links (Google Drive/Baidu)
# 2. Place it in D:\Projects\border surv\models\ChangeFormer\checkpoints\ChangeFormerV6_LEVIR\best_ckpt.pt
# (You might need to create the folders if they don't exist)

$env:PYTHONPATH = "D:\Projects\border surv\models\ChangeFormer"

Write-Output "Running ChangeFormer Inference Demo..."

# By default, demo_LEVIR.py uses images from samples_LEVIR folder
# To point it to our dataset, we can override --data_name, or just copy some images to samples_LEVIR.
# The easiest way is to let it run its default demo first!

$CHECKPOINT_DIR = "D:\Projects\border surv\models\ChangeFormer\checkpoints"

if (-not (Test-Path "$CHECKPOINT_DIR\ChangeFormerV6_LEVIR\best_ckpt.pt")) {
    Write-Output "WARNING: Pretrained weights not found!"
    Write-Output "Please place the downloaded .pt file as:"
    Write-Output "models\ChangeFormer\checkpoints\ChangeFormerV6_LEVIR\best_ckpt.pt"
    exit 1
}

& "D:\Projects\border surv\models\ChangeFormer\.venv\Scripts\python.exe" demo_LEVIR.py `
    --gpu_ids "-1" `
    --checkpoint_root $CHECKPOINT_DIR `
    --project_name "ChangeFormerV6_LEVIR" `
    --output_folder "samples_LEVIR\predict_CD_ChangeFormerV6"
