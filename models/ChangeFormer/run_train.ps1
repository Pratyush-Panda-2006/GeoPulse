# Prepare the configuration for training ChangeFormer on the processed LEVIR-CD dataset.
# The user specified NOT to run a long training yet, so this script is prepared but should be executed manually or with few epochs to test.
# RTX 4050 6GB Safe Configuration: Batch Size 4, Workers 2.

$env:PYTHONPATH = "D:\Projects\border surv\models\ChangeFormer"

$PROJECT_DIR = "D:\Projects\border surv\models\ChangeFormer"
$CHECKPOINT_DIR = "D:\Projects\border surv\models\ChangeFormer\checkpoints"
$VIS_DIR = "D:\Projects\border surv\models\ChangeFormer\vis"

if (-not (Test-Path $CHECKPOINT_DIR)) {
    New-Item -ItemType Directory -Path $CHECKPOINT_DIR | Out-Null
}

if (-not (Test-Path $VIS_DIR)) {
    New-Item -ItemType Directory -Path $VIS_DIR | Out-Null
}

Write-Output "Starting ChangeFormer Training on local LEVIR-CD dataset..."

# Configuration tuned for RTX 4050 6GB
# Batch size reduced to 4 to prevent OOM
# num_workers set to 2
& ".\.venv\Scripts\python.exe" main_cd.py `
    --data_name LEVIR `
    --batch_size 4 `
    --num_workers 2 `
    --max_epochs 100 `
    --lr 0.0001 `
    --checkpoint_root $CHECKPOINT_DIR `
    --vis_root $VIS_DIR `
    --net_G ChangeFormerV6 `
    --optimizer adamw `
    --loss ce `
    --img_size 256 `
    --embed_dim 256 `
    --split train `
    --split_val val
