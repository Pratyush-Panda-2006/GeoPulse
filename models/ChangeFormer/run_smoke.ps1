$env:PYTHONPATH = "D:\Projects\border surv\models\ChangeFormer"

$PROJECT_DIR = "D:\Projects\border surv\models\ChangeFormer"
$CHECKPOINT_DIR = "D:\Projects\border surv\models\ChangeFormer\checkpoints"
$VIS_DIR = "D:\Projects\border surv\models\ChangeFormer\vis"

Write-Output "Starting ChangeFormer 1-Epoch SMOKE TEST on local LEVIR-CD dataset..."

# We run for exactly 1 epoch
& ".\.venv\Scripts\python.exe" main_cd.py `
    --data_name LEVIR `
    --batch_size 4 `
    --num_workers 2 `
    --max_epochs 1 `
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
