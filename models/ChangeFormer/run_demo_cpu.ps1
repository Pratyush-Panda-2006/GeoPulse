$env:PYTHONPATH = "D:\Projects\border surv\models\ChangeFormer"

$CHECKPOINT_DIR = "D:\Projects\border surv\models\ChangeFormer\checkpoints"

Write-Output "Running ChangeFormer Inference Demo on CPU..."

& "D:\Projects\border surv\.venv\Scripts\python.exe" demo_LEVIR.py `
    --checkpoint_root $CHECKPOINT_DIR `
    --project_name "ChangeFormerV6_LEVIR" `
    --output_folder "samples_LEVIR\predict_CD_ChangeFormerV6" `
    --gpu_ids "-1"
