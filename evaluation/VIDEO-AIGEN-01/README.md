# VIDEO-AIGEN-01: fully AI-generated video, full pipeline

Measurement only; no setting was changed because of it.

- Fake: 40 Veo 3 and 40 HunyuanVideo clips, sampled with seed 0 from the
  downloaded `veo3/data_001.zip` and `hunyuanvideo/data_00{1,2}.zip`.
- Real: the 40 real DFD clips of `DFD_heldout80` (a different source, so source
  differences other than generation can affect these numbers).
- Command (two shards, default settings, `TRUFOR_ENABLED=false`):
  `python scripts/eval_end_to_end.py score-video --data C:/deepsentinel_data/AIVID_test --name video_aigen_veo3_hunyuan --shard K/2 --out-dir ../evaluation/VIDEO-AIGEN-01`
  then `summarise --out-dir ../evaluation/VIDEO-AIGEN-01`.

Results (`summary.json`): real called MANIPULATED 1/40; fake called MANIPULATED
14/80 (Veo 3 10/40, HunyuanVideo 4/40), INCONCLUSIVE 11/80, AUC 0.682.
The pipeline does not reliably detect fully AI-generated video. GenD only
scores faces, and the scene detectors are image models run on 8 frames.

The run logged "No such file or directory ... _keyframe.png" for the keyframe
image-forensics stage, which flagged nothing on either class. The cause is the
evaluation script: it uses the clip's folder path (`e2e-real/dfd_actors/...`) as
the job id, so the keyframe is written to a folder that does not exist. Uploads
use UUID job ids and are not affected. That stage carries no verdict weight, so
the verdict numbers above stand, but stage 4 should not be read from this run.
