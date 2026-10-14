# paper/analysis/

Analysis scripts that turn saved per-item score files in `paper_results/` into
`metrics.json`, LaTeX snippets in `paper/tables/` and figures in `paper/figures/`.

They must be deterministic and must not run any model, so that every table and
figure in the paper can be regenerated from saved files alone (Phase 9).
