# TruFor model code (vendored)

Copied unchanged from https://github.com/grip-unina/TruFor (`test_docker/src/models`, branch `main`,
fetched 2026-10-28), except one import in `cmx/builder_np_conf.py` made relative so the code works as a
package (marked "DeepSentinel" in a comment).

Guillaro, Cozzolino, Sud, Dufour, Verdoliva, "TruFor: Leveraging all-round clues for trustworthy image
forgery detection and localization", CVPR 2023.

Licence: `LICENSE.txt` (GRIP-UNINA): use, reproduction and modification only for informational and
nonprofit purposes; industrial or profit-oriented use is prohibited; notices must be kept; results made
public must cite the authors. `cmx/LICENSE_CMX.txt` covers the CMX parts. If DeepSentinel is ever used
commercially, set `TRUFOR_ENABLED=false` and remove this folder.

Weights are not in the repository: `app/ml/trufor.py` downloads `TruFor_weights.zip` from
https://www.grip.unina.it/download/prog/TruFor/TruFor_weights.zip on first use.
