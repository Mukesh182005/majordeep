# paper_results/

The only source of numbers for the paper. One folder per experiment, for
example `audio_asvspoof2019la/`, `image_h560/`, `image_t2/`.

Each folder contains:
- `config.json`: the experiment's settings plus the provenance record from
  `ml/provenance.py` (git commit, dirty flag, manifest sha256, seeds, library
  versions, GPU, command line, UTC time);
- the per-item score files (per utterance or per image);
- `metrics.json`, written by a script from those scores.

Every number used in the paper is listed in `INDEX.md` with the file and key it
comes from. Never write or edit a number here by hand.
