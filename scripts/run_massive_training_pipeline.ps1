$ErrorActionPreference = "Stop"
$REPO_ROOT = Split-Path -Parent $PSScriptRoot
Set-Location $REPO_ROOT

Write-Host "==========================================================="
Write-Host "DEEPFAKE DETECTION: MASSIVE SCALE-UP PIPELINE"
Write-Host "==========================================================="
Write-Host ""

Write-Host "[1/3] Generating 360,000 Social Media / Diffusion Images..."
python scripts\generate_massive_social_dataset.py
if ($LASTEXITCODE -ne 0) { throw "Image generation failed." }

Write-Host "`n[2/3] Expanding Training Dataset Manifest to 500,000 Images..."
python scripts\expand_training_dataset.py
if ($LASTEXITCODE -ne 0) { throw "Manifest expansion failed." }

# The synthetic-audio steps were removed: they generated NumPy tones and trained
# checkpoints/audio_detector.pt on them (retired; see KNOWN_ISSUES.md and
# scripts/archive/). The audio model is trained on ASVspoof 2019 LA with
# ml/training/train_asvspoof.py.

Write-Host "`n[3/3] Kicking off Fine-Tuning..."
Write-Host "  -> Launching Image Fine-Tuning (CPU Pipeline)..."
Start-Process "python" -ArgumentList "ml\training\finetune_image_detector.py --device cpu --batch-size 128 --workers 16" -NoNewWindow

Write-Host "`n==========================================================="
Write-Host "PIPELINE INITIATED SUCCESSFULLY"
Write-Host "==========================================================="
