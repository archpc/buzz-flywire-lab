# Dataset provenance

Sidecar record. The JSON datasets in this directory are immutable and are **not** modified.
Where a dataset's own metadata is incomplete or misleading, this file is the correction.
Shuffle seeds are given as hex = decimal, because the kernel logs hex while the JSON stores
decimal.

| File | Trials | Arms | Shuffle seed(s) | Where the seed is recorded |
|---|---|---|---|---|
| `escape_latency_intact.json` | 42 | intact | none | top-level `shuffle_seed: 0` (correct) |
| `escape_latency_shuffled.json` | 42 | shuffled | 0xC0FFEE = 12648430 | top-level (correct) |
| `escape_latency_shuffled_2.json` | 9 | shuffled | 0xDEADBE0F = 3735928335 | top-level (correct) |
| `ablation_battery.json` | 126 | intact, sham, 12 ablations | none | top-level `0` (correct) |
| `mirror_image.json` | 225 | 180 intact-kernel (intact/sham/loomL/loomR ablations) + 45 shuffled | 0xBAADF00D = 3131961357 | `shuffled_control.shuffle_seed`; top-level `0` describes the 180 intact-kernel trials only |
| `banana_peel.json` | 36 | 21 intact (15 sugar sweep + 6 loom controls), 15 shuffled | shuffled arm: 0xC0FFEE = 12648430 | **top-level `shuffle_seed: 0` is wrong for the shuffled arm**, see below |
| `runs/20261019t004219-second-helping/results.json` | 60 | intact, shuffle-0xC0FFEE, shuffle-0xFEEDF00D, shuffle-0x8BADF00D | per arm | per-trial `arm` label (correct) |
| `runs/20261019t-integration-check/escape_latency_intact.json` | 42 | intact | none | top-level (correct) |
| `runs/20261019T051238Z-maze/{intact,nostim}.json` | 3 + 3 | intact | none | top-level (correct); exploratory, not accepted |
| `runs/smoke-maze*.json` | 2 each | intact | none | exploratory smoke runs, not accepted |

## banana_peel.json: shuffle-seed correction

- **Defect:** the file merges two runs (shuffled arm first, intact arm second). The merge
  kept the metadata of the last run, the intact one, so top-level `shuffle_seed` reads `0`
  even though 15 of the 36 trials come from a shuffled connectome.
- **Correct value:** trials with `"arm": "shuffled"` used shuffle seed **0xC0FFEE
  (12648430)**. The trials with `"arm": "intact"` used no shuffle.
- **Evidence:**
  1. The bridge log for that run (`logs/bridge_banana_shuf.log`, not published) begins:
     `[2026-10-19 00:31:20,786] INFO: Spawning kernel: .../SiliconFly --serve --shuffle 0xC0FFEE`
     (bridge on port 8081).
  2. The companion intact log (`logs/bridge_banana.log`) shows the same spawn time without
     `--shuffle`, on port 8080.
  3. report_phase5 §2 ("Shuffled connectome (0xC0FFEE)").
- **Use the per-trial `arm` field, not the top-level `shuffle_seed`,** to split this
  dataset. `analyze_banana.py` already does this.
- Recorded 2026-10-24. Dataset bytes unchanged (verify with `shasum -a 256 data/banana_peel.json`).
