# Buzz lab — Phase II report: control bridge and escape-latency experiment
Date: 2026-10-19. Host: the test Mac (M5 Pro, 48 GB). Specimen: dawsonamf/siliconfly @ 8839d84, branch `lab-bridge` (commits 179dd61, 0bbf9e5). Bridge layer: lab.py + experiment/analysis scripts.

Evidence categories used throughout: OBSERVED (the simulation produced it), MODEL PREDICTION (what that implies under LIF+connectome assumptions), BIOLOGICAL EVIDENCE (independent living-fly experiments). A simulated response is not automatically a validated biological result.

## 1. What was built

- **Kernel control server** (`LabServer.swift`, `--serve`): headless JSON-lines protocol over stdin/stdout. Commands: hello, reset(seed), set_input, stimulate(group|neurons), step(ms), trial, read, membrane, shutdown. All operations synchronous, GPU work serialized by construction, line-buffered I/O.
- **`trial` primitive**: settle (zeroed sensory input) → hold loomL/loomR drive at 1 ms resolution → post-stimulus silence; returns per-step GF/LC/pop counts and first-GF latency in one call. This is the simtest phase-2 protocol, exposed programmatically.
- **Weights-shuffled control** (`--shuffle N`): seeded Fisher-Yates permutation of the int16 edge weights before GPU upload. Preserves the weight multiset (hence fixed-point overflow bound), degree sequences, group sizes; destroys wiring specificity. Mirrors Shiu et al.'s connectivity-weight shuffle. A neuron relabeling would be a no-op here because input targeting is role-keyed.
- **HTTP/JSON bridge** (`lab.py`, stdlib only): binds 127.0.0.1 only; spawns/kills the kernel; validates and clamps every parameter (step ≤ 120 s, stim ≤ 5 s and ≤ 2.0, trial ≤ 10 s, neuron-id bounds); translates HTTP↔JSON-lines; exposes /status /reset /step /stimulate /inject /trial /read /export /shutdown.
- **Makefile recipe**: `make build` (swiftc), `make test` (GPUCHECK), `make run` → headless bridge; `make fly` still launches the untouched GUI. `hermes verify --json --port 8080` = ok:true (build PASS, GPUCHECK PASS, readiness 200). Recorded 2026-10-19.
- The GUI app, ETL, diagnostics are unmodified; all changes are additive (LabServer.swift is a new file; main.swift gained one 4-line dispatch; build.sh gained one filename).

## 2. Validation (Phase 3) — all OBSERVED

- GPUCHECK: PASS (bit-exact CPU/GPU agreement, ascend-only |Δv| ≤ 1.19e-07 over 200 steps, 10.0 s).
- Determinism under the bridge: reset(seed=12345) → step(5000) twice → total_spikes = 1,214,159 both times, exactly.
- Bridge vs CLI baseline: the trial primitive reproduces simtest phase-2 behavior (GF silent at rest, fires on loom, first spike 3 ms at full loom — matching `--simtest`'s "abrupt loom 0.4s: first at 3 ms").
- The fly was not harmed: every malformed request observed during development (bad path, bad seed type, unknown group) returned a structured error; zero kernel crashes.

## 3. First experiment: Escape Latency Lab (Phase 4)

Design: 3 seeds (12345-12347 = three "individuals" via per-neuron baseline draws) × 2 durations (100/400 ms) × 7 loom intensities (0.0 = no-stim control … 1.0), through the REAL sensory port. Same sweep on the weights-shuffled connectome (seed 0xC0FFEE). 84 trials, ~2 min wall.

Results (OBSERVED, intact arm):
- No-stim (loomL=0): zero GF spikes in every trial. GF is silent at rest, as designed.
- GF first-spike latency is intensity-dependent and monotonic: loomL 0.2 → 24-53 ms; 0.4 → 7-8 ms; 0.6 → 4-5 ms; 0.8 → 3-4 ms; 1.0 → 3 ms.
- GF spike count scales with intensity and duration (25 spikes/100 ms at 1.0; ~101/400 ms at 1.0).
- Latency curves for 100 ms and 400 ms coincide from 0.4 upward: latency is set by the loom onset transient, not by how long the threat lasts. MODEL PREDICTION: the escape trigger is an onset detector above ~0.35 loom drive; sustained drive changes spike count, not trigger speed.
- Seed variability is real and structured: at near-threshold intensity (0.2), latency spans 24-53 ms across seeds — individual baseline draws shift effective excitability. This is the honest substitute for inventing noise.
- Threshold: lowest intensity producing any GF response = loomL 0.2 (all three seeds).

Control arm (OBSERVED, shuffled):
- **Zero GF spikes in all 42 trials**, at every intensity including 1.0.
- LC4/LPLC2 populations still respond to loom drive (rates rise ~8→34 Hz with intensity, and their no-stim baseline is elevated ~8-11 Hz vs 0 Hz intact) — input targeting is role-keyed and preserved, while global network dynamics changed.
- Dissociation: sensory drive survives the shuffle; the specific loom→GF pathway does not.

## 4. Scientific reading (Phase 6)

OBSERVED: the numbers above, produced by the Q16 LIF sim on the real v783 connectome.

MODEL PREDICTION: under the assumptions (LIF, weights = synapse count × sign from EM-predicted neurotransmitters, single free scale, no neuromodulation, no plasticity, hand-tuned resting drives and noise), the loom→LC→giant-fiber escape pathway is wiring-specific: it survives only with the true connectome. Escape latency in this model is governed by the onset volley through the calibrated gap-junction path (LC4/LPLC2→GF), giving a ~3 ms floor at saturation — consistent with the calibrations in the repo's tuning notes.

BIOLOGICAL EVIDENCE: in living flies, the giant fiber is indeed the looming/escape command neuron; optogenetic activation of LC4/LPLC2 inputs triggers escape; measured GF-mediated escape latencies are a few tens of ms from visual onset to jump (von Reyn et al. and successors). The simulated 3-50 ms latency band is the right order of magnitude — but that agreement is partly guaranteed by the repo's own calibration against such numbers, so it is consistency, not independent prediction.

What this experiment does NOT show: that the simulated GF response was predicted blind by the connectome (the GF input gains were hand-tuned to make the escape race work); that a shuffled connectome is a fair null for all circuits (it also changes global dynamics, as the elevated shuffled LC baseline shows); or anything about real behavioral thresholding in flies.

Honest note on the random-network critique (Turaga/Brunton): this result is the counter-example's first data point for ONE circuit — the shuffled control fails where the intact connectome succeeds, with matched group sizes and degree sequences. It does not yet answer the critique for locomotion, where Eon's body controllers dominate.

## 5. Limitations

- Single-shuffle control (one shuffle seed). Proper practice: several shuffle seeds. Cheap to add.
- GF input gains (gapJunctionBoost 0.5, sensGFBoost 1.5, gfInputScale 0.12) were hand-tuned upstream; latency results inherit those choices.
- No body: latency to takeoff, not just GF spike, would require the scripted SceneKit body or the flygym MuJoCo body.
- Loom is a scalar drive on the sensory port, not retinotopic angular expansion. "Angular expansion" is parameterized only as intensity; a true looming rake (expansion-rate sweep) would need the vision pipeline (Lappalainen-style) feeding loomL/loomR.
- 3 seeds, not a population study.

## 6. Recommended next experiment

**Ablation battery on the escape circuit** (Project 3 from Phase I): with the bridge in place, systematically stimulate/ablate each upstream population (LC4 vs LPLC2, sensory, ascending) and re-run the latency sweep, building a causal influence map of the escape pathway. Requires only a `--ablate group` kernel flag (zero the group's baseline and its outgoing edges). Then: multiple shuffle seeds to put an error bar on the control. Both are hours, not weeks, on the existing foundation.

## 7. Deliverable index

- Bridge: lab.py; kernel: specimen/LabServer.swift (committed 179dd61, 0bbf9e5)
- API docs: API.md; install: INSTALL.md
- Validation: hermes verify ok:true (build + GPUCHECK PASS + readiness 200); determinism check 1,214,159 = 1,214,159
- Datasets: data/escape_latency_intact.json (42 trials), escape_latency_shuffled.json (42 trials)
- Figure: figs/escape_latency_curves.png
- Experiment/analysis code: run_experiment.py, analyze_escape.py
