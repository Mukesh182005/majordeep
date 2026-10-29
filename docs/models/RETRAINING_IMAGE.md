# Keeping the image detector current

New image generators appear every few months, and a detector trained before a
generator existed usually misses it: before fine-tuning, Community Forensics
caught 2.6 % of GPT Image 2 and 0.5 % of Nano Banana 2 test images
(`evaluation/COMMFOR-FT-01/mllm_original.json`). This is the procedure for
adding a new generator. Every step writes a file; quote numbers only from those
files.

## 1. Collect images

- At least 1,000 images from the new generator, and real photos taken or
  downloaded the same way (same sites, same sizes). Check the licence of any
  dataset you use and record it in `docs/research/DATASETS.md`.
- Put them in a folder with a CSV listing `path, generator, category`
  (the format of `subset.csv` / `extra.csv`; see `ml/training/finetune_commfor.py`).
- Keep the test images out of training. `finetune_commfor.py` writes the split
  it used to `<checkpoint>/splits.csv`; extra images passed with `--extra-root`
  are training-only.

## 2. Train (about 15-30 minutes on the RTX 5070)

```powershell
python ml/training/finetune_commfor.py --mllm-root C:\deepsentinel_data\MLLM_subset `
    --e2e-root C:\deepsentinel_data\E2E_images --extra-root C:\deepsentinel_data\MLLM_extra `
    --strong-aug --epochs 12 --out checkpoints\commfor_ft_<name>
```

Every image, real and AI, is resized and re-encoded as JPEG before training, so
the file format (AI images are often PNG, real photos JPEG) cannot be learned as
a shortcut. `--strong-aug` adds blur, screenshot-style resampling and a second
JPEG pass so the model holds up on processed uploads. The epoch with the best
validation AUC is kept.

## 3. Calibrate on validation

```powershell
python ml/training/calibrate_commfor.py --ckpt checkpoints\commfor_ft_<name>
```

Fine-tuning shifts scores upward. This stores a logit offset in
`metadata.json` so that at most 1 % of validation real images score >= 0.5.
`CommForScorer` applies it automatically.

## 4. Test before switching

Score the new checkpoint and the current one on the same held-out sets, with
`COMMFOR_MODEL_ID` pointing at each:

```powershell
cd backend
$env:COMMFOR_MODEL_ID = "..\checkpoints\commfor_ft_<name>\model.safetensors"
python scripts/eval_scene_detectors.py --data C:\deepsentinel_data\MLLM_test_jpeg --out ..\evaluation\<RUN>\mllm.json --grid 0 4
python scripts/eval_scene_detectors.py --data C:\deepsentinel_data\E2E_images_test --out ..\evaluation\<RUN>\old.json --grid 0 4
python scripts/eval_scene_detectors.py --data C:\deepsentinel_data\ACC_TEST --out ..\evaluation\<RUN>\acc.json --grid 0 4
```

Switch only if the new checkpoint is better on the new generator **and** not
worse on older generators and on processed photos, with real photos flagged
staying at 1-2 %. Then set `COMMFOR_MODEL_ID` (config / `docker-compose.yml`),
re-run `scripts/eval_end_to_end.py`, and update `docs/research/EVALUATION.md`
from the result files.

## 5. Deploy

Checkpoints are not in git (`.gitignore`). Copy the checkpoint folder
(`model.safetensors` and `metadata.json`) to the server's `checkpoints/` and
check its SHA-256 against the one recorded in `EVALUATION.md`.
