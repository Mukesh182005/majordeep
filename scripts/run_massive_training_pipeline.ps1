$ErrorActionPreference = "Stop"
$REPO_ROOT = "C:\Users\STUDENT\Desktop\deepfake\deepfake"
Set-Location $REPO_ROOT

Write-Host "==========================================================="
Write-Host "DEEPFAKE DETECTION: MASSIVE SCALE-UP PIPELINE"
Write-Host "==========================================================="
Write-Host ""

Write-Host "[1/4] Generating 360,000 Social Media / Diffusion Images..."
python scripts\generate_massive_social_dataset.py
if ($LASTEXITCODE -ne 0) { throw "Image generation failed." }

Write-Host "`n[2/4] Expanding Training Dataset Manifest to 500,000 Images..."
python scripts\expand_training_dataset.py
if ($LASTEXITCODE -ne 0) { throw "Manifest expansion failed." }

Write-Host "`n[3/4] Generating 20 Hours of Audio..."
python scripts\generate_massive_audio_dataset.py
if ($LASTEXITCODE -ne 0) { throw "Audio generation failed." }

Write-Host "`n[4/4] Kicking off Fine-Tuning..."
Write-Host "  -> Launching Image Fine-Tuning (CPU Pipeline)..."
Start-Process "python" -ArgumentList "ml\training\finetune_image_detector.py --device cpu --batch-size 128 --workers 16" -NoNewWindow
Write-Host "  -> Launching Audio Fine-Tuning (CPU Pipeline)..."
Start-Process "python" -ArgumentList "ml\training\train_audio.py --device cpu --batch-size 64 --workers 8" -NoNewWindow

Write-Host "`n==========================================================="
Write-Host "PIPELINE INITIATED SUCCESSFULLY"
Write-Host "==========================================================="
