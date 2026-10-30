# AUDIO-FT2-01: second pellav2 fine-tune (rejected)

`ml/training/finetune_pellav2.py` as in the first attempt (E2E-03), plus 2,500
LibriSpeech clips of genuine speech (`--extra-bonafide C:/deepsentinel_data/LIBRI`),
each used clean and with two random codecs: 7,500 training windows. Best epoch 3 (validation AUC 0.996); calibration
left the logit bias at 0. Checkpoint: `checkpoints/pellav2_ft_v2/` (git-ignored).

Full pipeline, same 300 + 300 ASVspoof 5 eval clips as `E2E-01` (seed 0), with
`AUDIO_PELLAV2_MODEL_ID` and `AUDIO_PELLAV2_CONFIG_FILE` pointing at the checkpoint:

| | Original pellav2 (`E2E-01`) | This fine-tune (`summary.json`) |
|---|---|---|
| Real called MANIPULATED | 15.0 % | 4.7 % |
| Fake called MANIPULATED | 77.0 % | 62.7 % |
| AUC | 0.894 | 0.914 |

Rule fixed before testing: switch only if real false alarms fall below 15 % and
fakes caught drop by at most 5 points. Fakes caught dropped 14.3 points, so the
original pellav2 stays. The ASVspoof 2019 run was stopped once the rule had
failed; no ASVspoof 2019 numbers are reported for this checkpoint.
