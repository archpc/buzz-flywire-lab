# Buzz lab — Phase VI report: Second Helping (Poisson-faithful taste input)
Date: 2026-10-19. Immutable run: `data/runs/20261019t004219-second-helping/` (per the mandatory data-integrity convention; no accepted dataset was opened for writing).

## 1. Kernel work: Poisson-faithful taste port (objective 5)

- New taste input path in the Metal kernel: inputKind 5, per-step Bernoulli spike at `tasteP = rate_hz/1000`, depositing `tasteKick` (= the noise-kick scale, 0.25 threshold units), drawn from an INDEPENDENT PCG stream (`tasteSeed` = sim seed + fixed salt).
- Deterministic-guarantee preservation (objective 4): the existing noise draw is untouched; with the taste port off (`sugarRate = 0`, the default), no existing mode's arithmetic changes. VERIFIED: GPUCHECK PASS (bit-exact CPU/GPU) and simtest PASS after the change; StepParams stride 76 → 88 with matching metal/Swift structs.
- The taste stream is seeded from the sim seed: Poisson trials are deterministic-per-seed and reproducible — reproducible randomness, not script-level nondeterminism.
- LabServer maps the 21 sugar-GRN root IDs to specimen indices at load ("taste port wired to 21/21 sugar GRNs") and exposes `sugarRate` plus a `poisson` mode in stim_trial. Commit 3d7f130.

## 2. Shuffle-distribution vs the feeding circuit (objectives 1-3)

Deterministic-mode MN9 sweeps on two NEW independently shuffled connectomes (0xFEEDF00D, 0x8BADF00D; 3 seeds × 5 levels each):

| arm | MN9 response to sugar drive | verdict |
|---|---|---|
| intact (Phase V) | 19-26 baseline → 74-87, monotonic all seeds | positive |
| shuffle 0xC0FFEE (Phase V) | flat 13-14 at every level | null |
| shuffle 0xFEEDF00D (new) | flat 14-16 at every level | null |
| shuffle 0x8BADF00D (new) | flat 14-20 at every level | null |

OBSERVED: 0 of 3 independently shuffled connectomes retain a feeding response, vs 1 of 3 for the escape circuit (Phase IV's 0xBAADF00D remnant). MODEL PREDICTION: the reconstructed feeding pathway (GRNs → interneurons → MN9) is more wiring-specific than the escape circuit under this control — plausibly because it is a longer chain (2 hops) with a narrow excitatory bottleneck (+94 through 13 interneurons) versus the escape circuit's direct calibrated gap-junction path. The distribution statement is now quantified per circuit, not global.

## 3. Poisson-faithful gustatory input (OBSERVED)

Intact connectome, MN9 spikes per 1.2 s trial:

| rate | seed 12345 | seed 12346 | seed 12347 |
|---|---|---|---|
| 0 Hz | 26 | 23 | 19 |
| 50 Hz | 16 | 29 | 20 |
| 100 Hz | 34 | 30 | 18 |
| 200 Hz | 41 | 31 | 22 |
| 400 Hz | 52 | 44 | 35 |

- Response is present and dose-dependent above ~100 Hz. At the Shiu-protocol rate (200 Hz): 41/31/22 vs baseline 26/23/19 — positive in all seeds.
- Drive-scale cross-check: 400 Hz × 0.25 kick = 0.1 threshold-units/step mean, matching the deterministic 0.1-strength trials (Phase V: 33-47). Poisson-observed 35-52. Consistent — the two drive classes agree where their mean drives match.
- Non-monotonicity at 50 Hz in one seed (26 → 16): low-rate Poisson input displaces the GRNs' baseline network-driven spikes (spike-dependent refractory displacement). Recorded as an observed property of fluctuation-driven regimes, not smoothed over.
- Shuffled arm (0xC0FFEE) under the faithful protocol: flat 14 at EVERY rate including 400 Hz. The feeding null survives the protocol upgrade.

## 4. Cross-circuit checks
GF spikes = 0 in all 60 Phase VI trials. Taste input does not recruit the escape circuit.

## 5. Testable predictions generated (objective 6)
1. The feeding bottleneck (+94 net signed weight through 13 identified interneurons) is the rate-limiting element: ablating those 13 interneurons should abolish the MN9 response while leaving the escape circuit untouched. (Falsifiable with the existing ablation machinery.)
2. The right-hemisphere sugar-GRN set from the reference notebook (20/21 present in v783) should also drive MN9 if the pathway is bilateral — or fail if it is lateralized like the escape circuit. Untested; one sweep answers it.
3. Connectome-structural: MN9's predominantly inhibitory direct input sum (-683 signed) with net-excitatory feeding-pathway input (+94) predicts that MN9 sits in an inhibition-gated configuration — checkable against the reference model's silencing experiments.

## 6. Compliance
- Immutable runs: this phase wrote only to `data/runs/20261019t004219-second-helping/`; no accepted dataset touched.
- No parameters adjusted to improve agreement; the sweep grid was pre-declared in the run script.
- Original specimen preserved; kernel change is additive (commit 3d7f130), taste-off behavior bit-identical.
- No persistent services; all bridges terminated after runs.

## 7. Limitations
- tasteKick fixed at the noise-kick scale (0.25); the true quantal size of a GRN synapse onto the feeding interneurons is not independently constrained here.
- 3 seeds per arm; 5 shuffle seeds total across both circuits.
- MN9 remains a single identified neuron (root-ID-exact mapping from the reference annotations); additional MN9-class readouts would strengthen the readout.
- Phase VI trial count: 60 (30 deterministic + 30 Poisson). Running total: 540.

