# Wait for audio generation to complete if not already done, then preprocess and train
$ErrorActionPreference = "Stop"

Write-Host "Starting 20GB Audio Synthesis..."
.venv\Scripts\python.exe scripts\generate_massive_audio_dataset.py

Write-Host "Starting Audio Dataset Preprocessing..."
.venv\Scripts\python.exe ml\preprocessing\build_audio_dataset.py --bonafide-dir data\raw\massive_audio\bonafide --spoof-dir data\raw\massive_audio\spoofed --output data\processed\audio_massive --window 4.0

Write-Host "Starting Accelerated Audio Model Training..."
.venv\Scripts\python.exe ml\training\train_audio.py --data data\processed\audio_massive --device cuda --epochs 10 --batch-size 128 --workers 4
