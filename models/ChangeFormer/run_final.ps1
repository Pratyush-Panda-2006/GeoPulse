$OUTPUT_LOG = "D:\Projects\border surv\models\ChangeFormer\final_output.txt"
$PYTHON_EXEC = "D:\Projects\border surv\models\ChangeFormer\.venv\Scripts\python.exe"
$DEMO_SCRIPT = "D:\Projects\border surv\models\ChangeFormer\run_demo.ps1"

Function Log-Info {
    Param([string]$Message)
    $TimeStamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$TimeStamp] $Message"
    Write-Output $LogMessage
    Add-Content -Path $OUTPUT_LOG -Value $LogMessage
}

Log-Info "Waiting for PyTorch CUDA to finish installing..."
while ($true) {
    $check = & $PYTHON_EXEC -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')" 2>&1
    if ($LASTEXITCODE -eq 0 -and $check -match "CUDA: True") {
        Log-Info "PyTorch with CUDA is installed and ready!"
        break
    } else {
        Log-Info "PyTorch not ready yet. Waiting 60 seconds..."
        Start-Sleep -Seconds 60
    }
}

Log-Info "Running inference demo..."
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
& powershell.exe -ExecutionPolicy Bypass -File $DEMO_SCRIPT | Tee-Object -Append -FilePath $OUTPUT_LOG
$stopwatch.Stop()
Log-Info "Inference completed in $($stopwatch.Elapsed.TotalSeconds) seconds."
Log-Info "Check samples_LEVIR\predict_CD_ChangeFormerV6 for output masks."
