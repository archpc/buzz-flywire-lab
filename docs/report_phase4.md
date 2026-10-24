# Buzz lab — Phase IV report: Mirror Image (bilateral looming)
Date: 2026-10-19. Run after passing all seven Phase III verification conditions (4/4 endpoint smoke + fresh GPUCHECK). No kernel changes required; the trial primitive already accepted independent loomL/loomR drive.

## Protocol compliance
1. Left/right/bilateral stimulation tested independently: YES (3 sides × 3 levels).
2. Bilateral stimulation at matched intensities: YES (loomL=loomR at each level).
3. Mirrored ablations under all conditions: YES (ablate:loomL and ablate:loomR × all 3 stimulus sides).
4. GF latency + spike counts recorded: YES (plus DNa L/R steering rates and population rates).
5. Controls: intact baseline, size-matched sham (314, seed 7), shuffled network — now THREE independent shuffle seeds (0xC0FFEE, 0xDEADBE0F, 0xBAADF00D).
6. Multiple seeds: 5 initialization seeds (12345-12349) = independent network realizations.
7. Original parameters preserved: YES; ablate_clear restoration verified after the run.

Matrix: 4 conditions × 3 sides × 3 levels × 5 seeds = 180 intact-arm trials + 45 shuffled-control trials = 225.

## Results (OBSERVED)

### Condition × stimulus side (mean GF spikes, 15 trials each)

| condition | stim L | stim R | stim B |
|---|---|---|---|
| intact | 66.7 | 82.0 | 152.3 |
| sham (314 random) | 67.4 | 81.9 | 153.7 |
| ablate loomL | **0.0** | 82.1 | 82.1 |
| ablate loomR | 66.7 | **0.0** | 66.7 |

Median GF first-spike latency: 4 ms in every firing condition, both sides. No latency asymmetry.

### Finding 1 — Lateralization now mirror-verified (OBSERVED)
The ablation × side interaction is a perfect cross: ablating the left looming detectors abolishes the response ONLY to left-port stimulation (0/15) while leaving the right-port response at full intact magnitude (82.1 vs 82.0); ablating the right side does the exact opposite (0/15 right; 66.7 = 66.7 intact-left). Bilateral responses collapse to the surviving side's magnitude. The Phase III ipsilaterality claim, which review correctly flagged as one-sided, is now supported under mirrored testing.

### Finding 2 — The source of the left/right magnitude asymmetry is the connectome itself (OBSERVED + forensics)
Right-port stimuli produce ~23% more GF spikes than left (82.0 vs 66.7), identical latency. Connectivity forensics on the raw v783 data: LC4/LPLC2→GF edge counts are nearly symmetric (right 145, left 148) but total |synapse weight| is asymmetric: right 1053 vs left 832 (+27%). The behavioral ratio (1.23) matches the structural ratio (1.27). Per protocol, the source was investigated BEFORE any model modification: the asymmetry is in the reconstructed connectome data, not an artifact of the stimulus protocol, the bridge, or the ablation machinery (sham shows the same 82/67 asymmetry). No model modification was made.

MODEL PREDICTION: under the LIF model, the right-eye looming pathway is intrinsically ~25% stronger at the GF. Whether the real fly's GF receives asymmetric bilateral input is testable in the literature/annotation data — this is a falsifiable model output, not a tuned artifact.

BIOLOGICAL EVIDENCE: the real giant fiber integrates binocular looming input with reported contralateral/ipsilateral response components; lateralization of escape direction (flies jump away from the threatening side) is established. The model's side-specific necessity is consistent in kind; its +27% right-dominance is a novel, checkable prediction from this connectome reconstruction.

### Finding 3 — Bilateral responses are additive (OBSERVED)
B = 152.3 vs L+R = 148.7 (102%). No occlusion, no sublinear summation at these intensities. The two side pathways converge on the GF nearly independently.

### Finding 4 — Shuffle controls are a DISTRIBUTION, not a constant (OBSERVED — new)
Shuffle seed 3 (0xBAADF00D) produced GF responses in 30/45 trials — but ONLY to right-port stimulation (L: 0/15; R: 15/15 at mean 4.8-24.0 spikes; B tracks R), and ~4-12× weaker than intact. Shuffles 1-2 remain at zero across all 96 trials run to date. The reviewer's correction ("two shuffled networks are insufficient for a general conclusion") is now empirically vindicated: the shuffled control is a random variable over which weights land on the ~290 LC→GF edges.

Source investigation (before any modification): replicating the kernel's exact shuffle in Python shows post-shuffle LC→GF |w| sums of 485/493 (0xC0FFEE), 492/504 (0xDEADBE0F), 699/599 (0xBAADF00D) vs intact 832/1053. Seeds 1-2 landed well below intact drive; seed 3 landed near-threshold with a degraded, right-port-only remnant (its residual firing is an order of magnitude below intact and not a functioning escape circuit). Note the simple |w|-sum account is incomplete: the shuffle also redraws the GF's ~3,650 ordinary in-edges (|w| mean 3.6, max 59-179) and the whole network's dynamics, so delivered (spike-gated) drive, not just static weight sums, decides the outcome. Full attribution would require per-edge delivery instrumentation in the kernel — listed as an optional follow-up, not undertaken (no model modification made).

### Finding 5 — Steering reads contralateral to the stimulus (OBSERVED, unexplained)
Under left-port stimulus, post-trial DNa rates are right-heavy (dnaL 41 / dnaR 50 Hz); under right-port stimulus, left-heavy (51/44). Same in sham. MODEL PREDICTION: the connectome's downstream steering readout responds contralaterally to a unilateral looming threat. Consistent with turning away from the threat; untested against unilateral-stimulus steering data. Recorded as a hypothesis for the next cycle.

## Negative findings
- No latency asymmetry anywhere (4 ms both sides, all conditions).
- Sham replicates intact exactly on every metric, both sides.
- No condition showed a partial/intermediate GF state: responses were either intact-magnitude or zero, except the near-threshold shuffled seed 3.

## Evidence
- Dataset: data/mirror_image.json (225 trials incl. shuffled arm)
- Figure: figs/mirror_image.png
- Forensics script output: LC→GF edge/weight analysis (this session log; rerunnable from specimen/data via the manifest)
- Experiment/analysis: run_mirror.py, analyze_mirror.py
- No kernel changes this phase; specimen unchanged at commit 64c3f79

## Limitations
- Loom is scalar drive at a port, not retinotopic angular expansion (unchanged from Phase II).
- 5 seeds; the shuffle-seed distribution is characterized by n=3 seeds (one positive, two negative).
- |w|-sum forensics is static; spike-gated delivery attribution not instrumented.
- MN9/steering interpretations are model-scoped.
