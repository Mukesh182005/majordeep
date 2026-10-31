# AUDIO-PHONE-01: the audio verdict on phone-quality and crowd-recorded speech

Measurement of the current default (pellav2 decides); no setting changed. Rules: `evaluation/ROUND4-RULES.md`.

Data (Hugging Face `34data` copies, 300 clips per source, seed 0; split 40 % validation / 60 % test by a hash
of the speaker where the file name has one, else of the file; built in the round-4 session):

- real: `v14-real-nisqa-corpus-dataset` (NISQA corpus: speech passed through telephone and VoIP
  conditions), `cvoice-small-real` (Common Voice German, crowd-recorded on users' own devices),
  `audiospoofing-mini-real`;
- AI: `cvoice-small-fake` (voice clones of Common Voice speakers), `audiospoofing-mini-fake` (CosyVoice).

Licences of these copies were not checked; used for evaluation only.

Command (from `backend/`, default settings):
`python scripts/eval_end_to_end.py score-audio --data C:/deepsentinel_data/PHONE_TEST --name audio_phone_test_baseline --shard K/2 --out-dir ../evaluation/AUDIO-PHONE-01`
(and `PHONE_VAL` / `audio_phone_val_baseline`), then `summarise`.

## Results (`summary.json`, test split, 561 real + 377 AI clips, 0 unresolved errors)

| | Called MANIPULATED | INCONCLUSIVE |
|---|---|---|
| Real, all | 4 / 561 (0.7 %) | 3 |
| Real, NISQA (telephone conditions) | 4 / 179 | 1 |
| Real, Common Voice | 0 / 178 | 0 |
| Real, audiospoofing-mini | 0 / 204 | 2 |
| AI, all | 305 / 377 (80.9 %) | 30 |
| AI, CosyVoice | 197 / 205 | 7 |
| AI, Common Voice clones | 108 / 172 | 23 |

Verdict AUC 0.969. The validation split agrees (real 0.6 %, AI 75.3 %).

## Conclusion

On this phone-quality and crowd-recorded speech the audio verdict rarely accuses real speech (0.7 %),
unlike the ASVspoof 5 sample (15 %, dominated by neural codecs; KNOWN_ISSUES #16). The weakness here is
missed clones: 41 of 172 Common Voice clones were called AUTHENTIC and 23 INCONCLUSIVE. The round-4 rule only allowed a change
that lowers real false alarms, which are already near zero, so no audio change is adopted.

Process note: the first attempt ran out of memory because a failed savefig leaked figures (fixed in
`app/ml/audio/signal_lab.py`); clips that failed were retried after the fix, and the evaluator's shard
retry bug (failures counted as done) was fixed in `scripts/eval_end_to_end.py`.
