# Buzz lab — Phase I report: whole-brain fly simulation survey on Apple Silicon
Date: 2026-10-19. Machine: the test Mac (MacBook Pro 14" M5 Pro, 15-core, 48 GB, macOS 26.6.1).
Labels: VERIFIED (executed or read directly this session), REPORTED (claimed by source, unverified), INFERRED (reasoned), SPECULATIVE (unfounded guess).

---

## 1. Executive findings

- YES: a biologically grounded whole fruit-fly brain (the FlyWire connectome: 139,255 neurons, 54.5M synapses) runs on your Mac, interactively, faster than real time. VERIFIED on the test Mac this session: siliconfly (Metal LIF over the full FAFB v783 connectome) built from source in seconds and ran at 58 µs/simulated-ms in batched mode (17.2x real-time) and 233 µs/step in single-step dispatch (4.3x real-time), with peak RSS of 250 MB. GPU/CPU bit-exactness verified by its own GPUCHECK (PASS).
- The scientific core is peer-reviewed: Shiu et al., Nature 634:210-219 (2024), DOI 10.1038/s41586-024-07763-9 — LIF whole-brain model on FlyWire, one free parameter (W_syn), neurotransmitter-derived signs (Eckstein et al., Cell 2024), 164 published testable predictions, 91% agreement (84% excluding split-GAL4 optogenetics). VERIFIED (paper read).
- The famous "we've uploaded a fruit fly" demo (Eon Systems, Mar 2026) is NOT peer-reviewed and its embodied behavior is mostly the hand-built body controller plus a handful of hand-picked descending neurons. Expert critics (Turaga, Cowley, Brunton's "digital sphinx") argue a random network through the same interface could walk. VERIFIED (critiques read).
- Memory is a non-issue: the full sparse network is ~0.4-0.7 GB. VERIFIED (~0.65 GiB measured in my NumPy benchmark). Only dense representations fail.
- Throughput verdicts (measured on the test Mac):
  - Metal LIF (siliconfly): 17x real-time batched, 4.3x single-step. VERIFIED.
  - Naive NumPy event-driven LIF, full 54.5M synapses: 0.10x real-time (9.81 s wall per biological second). VERIFIED. This is the honest floor for Python-level implementations.
  - Brian2 C++ standalone (Eon fly-brain repo, Brian2 CPU backend): 0.257x real-time on the test Mac; spike count 1568 vs 1558 on Eon's Linux run — near-exact reproducibility. VERIFIED.
  - NeuroMechFly v2 MuJoCo body physics (flygym 2.1.1): 38.8x real-time stepping (ground-contact sensors disabled due to an upstream bug). VERIFIED with that caveat.
- Best implementation for the test Mac: siliconfly (interactive, Apple-native, full connectome, proven on your GPU) + Eon's fly-brain repo as the scriptable scientific benchmark harness. flygym as the embodied-body lab. flysim as the control-plane play (HTTP API) if you approve an 852 MB data download.
- Mac mini M4: viable headless host for event-driven LIF (memory trivial, bandwidth adequate at fly firing rates). INFERRED; thermals unverified.

## 2. Comparison of implementations

| Project | Verdict (A/B/C/D) | Dataset | Model | GPU | Apple Silicon | License | Status |
|---|---|---|---|---|---|---|---|
| siliconfly (dawsonamf) | B + decorative body | FlyWire/FAFB v783 full (139,255 n; 15.09M edges; 54.49M syn, bundled ~95 MB) | LIF, 1 kHz, Q16 fixed-point, Dale signs, no plasticity | Metal (2 kernels/ms) | Native, macOS 15+, built+ran on the test Mac | MIT code, CC BY-NC 4.0 data | 4 commits, Aug 2026, 7 stars |
| flysim (mikewolak) | B + scripted env | FlyWire v783 proofread feather (852 MB download; "16.8M synapses" is actually edge count) | LIF (-52/-45 mV, tau 20/5 ms), Q14 fixed-point | Metal + CPU pthreads | Native ObjC app | Custom educational-only (not OSI) | 26 commits, Jun 2026, 8 stars |
| Eon fly-brain | D (benchmark/prediction) | FlyWire v783 aggregated pairs (~138k n, ~5M "synapses" = pair table) | Shiu-style LIF, w=signed syn count | CUDA backends only | Brian2 CPU + PyTorch CPU work (verified Brian2) | GPL-2.0 | 15 commits, 994 stars |
| FlyWire | A (data/tooling) | FAFB v783 reference dataset | n/a | n/a | codex.flywire.ai exports; python fafbseg/navis | data is CC BY-NC (per siliconfly DATA_LICENSE) | current release |
| flygym (NeLy-EPFL) | C (embodied body) | NeuroMechFly v2 morphology, not connectome | MuJoCo body; brain is YOUR plug-in | warp extra NVIDIA-only | CPU physics VERIFIED 38.8x RT | Apache-2.0 | active, v2.1.0/2.1.1 |
| FastFly (eonfathom) | B (claimed) | v783 full | GPU LIF | CUDA | No | unverified | 12 stars, claims unverified |

Notes:
- A=connectome visualization, B=activity simulation, C=embodied behavior, D=biological prediction.
- Synapse-count forensics: siliconfly bundles the true 54,492,922-synapse graph (its etl.py prints the totals). flysim's "16.8M synapses" is the count of edge rows (convert_flywire.py:154 sets E=len(indices)). Eon's "~5M synapses" is the aggregated pair table. VERIFIED (code read).
- Eon's embodied-fly demo lives on their website, not in this repo; the repo contains only the simulator benchmark. VERIFIED.
- Nobody ships a peer-reviewed closed-loop brain+body pipeline. Shiu 2024 is unembodied (feeding + antennal grooming predictions; no NeuroMechFly coupling in the paper). Eon coupled them informally. INFERRED from paper + Eon pages.

## 3. Recommended implementation for the test Mac

Primary: siliconfly. Reasons: only project that bundles the full 54.5M-synapse connectome and runs it on Metal faster than real time; already built and verified on the test Mac (see Section 4); MIT code; interactive brain view with click-to-stimulate; the body is procedural (be honest with yourself about that — the walking is scripted, the neural drive is real).

Scientific harness: eonsystemspbc/fly-brain. Runs on the test Mac CPU (verified), GPL-2.0, and gives you the Shiu model lineage with clean benchmarking and spike parquet outputs Hermes can chew on.

Embodiment: flygym v2.1.1 (Apache-2.0) — MuJoCo fly with vision, olfaction, terrain; verified at 38.8x RT physics-only stepping on the test Mac. Coupling a connectome brain to it is the real research frontier (Eon did it with a 15 ms sync step; nobody has published it peer-reviewed).

Not recommended: PyTorch MPS as the sim engine (kernel-launch overhead + scatter/gather bugs; the >2^31-element gather zero-row bug on torch 2.12/2.13 is VERIFIED upstream), MLX for per-spike scatter (dense-array design, wrong fit), any CUDA-only path (Brian2CUDA/GeNN/NEST GPU).

## 4. Installation and execution (VERIFIED procedures)

All work was done in isolated scratch dirs; nothing was installed system-wide, no services created, Hermes config untouched.

### siliconfly — built and verified on the test Mac
- Repo: https://github.com/dawsonamf/siliconfly @ 8839d84 (shallow clone in ~/.hermes/cache/scratch/drosophila/repos/siliconfly)
- Requirements: Xcode (export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer), macOS 15+. Data ships in the repo (~95 MB).
- Build (one command): `swiftc -O -swift-version 5 -o SiliconFly main.swift FlyModel.swift Sim.swift MetalSim.swift GPUCheck.swift Diagnostics.swift BrainView.swift Environment.swift -framework Cocoa -framework SceneKit -framework Metal`
- Run GUI: `./SiliconFly` (brain view + desktop fly). Headless validation:
  - `./SiliconFly --gpucheck` → GPUCHECK PASS (bit-exact CPU/GPU, determinism over 200-step batches)
  - `./SiliconFly --simtest` → full diagnostic suite (see Section 5 numbers)
- Storage: ~500 MB clone incl. data. Peak RSS at runtime: 250.7 MB. VERIFIED (/usr/bin/time -l).
- Failure modes seen: none. Builds clean with warnings only.

### Eon fly-brain — Brian2 CPU verified on the test Mac
- Repo clone at repos/fly-brain (data included: 2025_Connectivity_783.parquet 100.8 MB).
- Env: `uv venv poc/flybrain-venv --python 3.12; uv pip install brian2 pyarrow pandas joblib`
- Run: `python main.py --brian2-cpu --t_run 0.1 --n_run 1` (underscore flags; argparse chokes on dashes). First run compiles C++ standalone (~3.6 s build). Results append to data/benchmark-results.csv + spike parquet.
- My result: setup 1.542 s, build 3.576 s, sim 0.389 s for 0.1 s bio → realtime_ratio 0.2568, 1568 spikes, 351 active neurons. Eon's own Linux brian2cpp rows sit in the same CSV: 0.1437 ratio, 1558 spikes. VERIFIED.
- Gotcha: environment.yml is CUDA-pinned; ignore it, use the CPU backend only.

### flygym — verified on the test Mac (with a caveat)
- `uv venv poc/flygym-venv --python 3.12; uv pip install "flygym @ git+https://github.com/NeLy-EPFL/flygym"` (PyPI `flygym` is a DIFFERENT, name-squatted package — do not use).
- Requires Python >=3.12, mujoco 3.9/3.10. Do NOT install the warp extra on macOS (NVIDIA-only).
- v2.1.0 and dev-v2.1.1 both hit an upstream bug: `ValueError: unrecognized name 'nmf/lf_coxa' of sensorized object` when attaching NeuroMechFly to FlatGroundWorld with ground-contact sensors. Workaround verified: `world.add_fly(fly, pos, rot, add_ground_contact_sensors=False)`. Bench result: 2000 steps (0.2 s bio at dt=1e-4) in 0.01 s → 38.8x real-time. Caveat: sensors off and no active locomotion, so treat as an upper bound on body-stepping cost. The old v1 API lives at tag v1.2.1.
- flysim: NOT built (needs 852 MB Zenodo download — requires your approval; license is educational-only anyway). Its control-plane details are documented in findings-A-repos.md.

## 5. Hardware performance expectations (the test Mac, M5 Pro 48 GB)

Measured this session:
- siliconfly Metal LIF: 58 µs/step batched (17.2x RT), 233-237 µs/step unbatched (4.3x RT), 229-249 spikes/step typical, 250 MB RSS. GPUCHECK PASS.
- Full-scale NumPy LIF (139,255 neurons / 54.4M synapses, 1 kHz, ~30 Hz mean rate): 9.81 s wall per 1 s bio (0.10x RT), worst step 14 ms, connectome storage 0.65 GiB. Conclusion: Python-level per-spike fan-out is the bottleneck; compiled kernels fix it — which siliconfly already is.
- Brian2 CPU: 0.26x RT (see above). Honest, deterministic, good as ground truth; not the interactive path.
- flygym MuJoCo stepping: 38.8x RT (caveated).

Inferred/reported context:
- Event-driven analysis: mean fan-out ~392 synapses/neuron; at fly-like rates (1-10 Hz) synaptic event traffic is 5e7-5e8 events/s, ~4 GB/s worst case — well within Apple Silicon bandwidth; per-spike random-access latency dominates, which favors multicore CPU or the existing Metal path. INFERRED.
- Dense connectivity fails memory (77 GB fp32); sparse always fits. INFERRED, confirmed by measurement.
- Mac mini M4 (120 GB/s base): adequate for event-driven LIF at fly rates; the real questions are sustained thermals and always-on behavior — unverified, test with powermetrics before committing it as a watch host. INFERRED.

## 6. What you can actually do (demonstrated vs speculative)

Demonstrated on the test Mac today (VERIFIED via siliconfly --simtest):
- Loom → LC population 172.5 Hz, giant fiber fires 147 spikes, first spike at 3 ms; GF silent at rest (escape circuit works).
- Left-eye loom flips DNa L/R rate difference from -16.1 to -22.5 Hz (steering signal is real and directional).
- Click-stimulating the DNg11 cluster drives grooming drive to 196 Hz.
- Spontaneous population ~1.7 Hz/neuron; 12.2 s continuous run with population drift 1.71→5.52 Hz.
- flysim's HTTP control plane (localhost:7777, SSE streams, /data/* readouts, /tool/* commands: run/stop/step/clamp/stimulus/backend/speed) — documented, not run. This is the single best Hermes integration surface that already exists.

Scientifically demonstrated in the literature (VERIFIED from papers):
- Shiu 2024: taste → feeding circuit predictions, antennal grooming circuit predictions, optogenetic validation of 164 predictions (91%). Also predicts failures honestly (basal-inhibition-dependent and neuromodulatory circuits are missed).
- Lappalainen 2024: connectome-constrained networks predict visual-system activity.
- NeuroMechFly v2 + Vaxenburg 2025: the body side is mature (walking, flight, terrain).

What is NOT demonstrated anywhere (SPECULATIVE territory, be honest):
- Emergent locomotion from connectome activity alone (all demos use scripted or imitation-trained controllers; Turaga's random-network critique stands unanswered).
- Learning/plasticity: none of these models have it. LIF + fixed weights. Adding biologically defensible plasticity is an open research problem, not an afternoon hack.
- Vision that actually drives behavior (Eon calls their visual input "decorative").

## 7. Hermes integration architecture

Three viable tiers, in order of effort:

Tier 1 — drive flysim's existing control plane (days):
  Hermes (execute_code or a cron) → HTTP to 127.0.0.1:7777 → POST /tool/step|clamp|stimulus, GET /data/spikes|populations|behavior, GET /stream (SSE). Requires the 852 MB data download (your approval) and acceptance of the educational license. Security note: server binds localhost with CORS * and no auth — fine for local use, don't expose via Tailscale without a fronting proxy.

Tier 2 — wrap siliconfly (recommended, ~a week of evenings):
  siliconfly is pure Swift with a clean MetalSim core but CLI-only control. Add a tiny HTTP/JSON endpoint (or a companion CLI that streams state as JSON lines) exposing: inject current into neuron IDs, read population rates, read DNa/DNp/GF outputs, step-count sync. Then Hermes conducts experiments: stimulate LC4, measure GF latency distributions, ablate DNa02, record spike parquet, analyze with numpy. The GPUCHECK infrastructure already proves the sim is deterministic — ideal for reproducible agent-run experiments.

Tier 3 — research-grade: Shiu-style Brian2/NumPy brain coupled to flygym body (Eon's architecture, 15 ms sync loop). Hermes designs experiments (odor gradient navigation, loom-escape statistics), runs them headless on the M4 mini, writes results to parquet, and does the analysis itself. This is the "Hermes as autonomous neuroscientist" endgame. Computationally trivial for the body (38x RT) and feasible for the brain (0.26x RT Brian2 or better in NumPy/C).

Long-running experiments on the M4 mini: yes, plausible — the network is 0.7 GB, spike recording at 10 Hz mean is 5.6 MB/simulated-second (5.6 GB per 1000 s if you keep everything; stream or aggregate). INFERRED. Set up as a manual process first (launchd only if you explicitly want a persistent service).

## 8. Five proposed projects (ranked)

1. "Escape latency lab" — introductory + scientific (siliconfly)
   Objective: measure giant-fiber escape-circuit latency distributions under looming stimuli of varying angular expansion.
   Capabilities needed: spike injection + GF readout (already in --simtest; needs Tier-2 API for automation).
   Effort: low. Cost: trivial (250 MB RSS, 17x RT). Output: latency histograms, threshold-expansion curves.
   Biological validity: high — looming-escape via LC4/LPLC2→GF is a canonical, experimentally measured circuit.
   Feasibility 10/10, science 6/10, fun 7/10.

2. "Connectome particle board" — interactive visualization (siliconfly + custom)
   Objective: native macOS (Metal + SwiftUI/AppKit) 3D view of all 139k somas with live spike glow, click-to-stimulate, circuit-highlight (feed it the FlyWire cell-type annotations), replay recorded runs.
   Effort: medium (SceneKit already does the hard part in siliconfly; you'd extend BrainView). Cost: trivial.
   Biological validity: n/a (visualization), but uses real coordinates bundled in the repo.
   Feasibility 9/10, entertainment 9/10, science 4/10.

3. "Ablation battery" — neural stimulation experiment (Eon fly-brain harness)
   Objective: systematically stimulate/silence each of ~50 well-annotated command populations (via the parquet's cell-type labels), record downstream rate changes, build a causal influence map. Compare against shuffled-weight control.
   Effort: medium. Cost: 0.26x RT per 0.1 s run → thousands of conditions per hour.
   Output: influence matrix; direct comparison with Shiu's published predictions (91% claim, testable!).
   Biological validity: as good as the LIF model's (caveats: no neuromodulation, fixed weights).
   Feasibility 9/10, science 8/10, fun 5/10.

4. "Brain-in-a-body" — embodied behavior (flygym + connectome brain)
   Objective: wire DNa01/02 + oDN1 population rates from a NumPy/C LIF brain into flygym's steering/velocity actuators, 15 ms sync (Eon's architecture), run bar-tracking and odor-gradient navigation in MuJoCo.
   Key scientific move Eon skipped: run the RANDOM-NETWORK CONTROL (same interface, shuffled weights) — if the connectome brain navigates better than the random brain, that's a publishable-grade demonstration on a laptop.
   Effort: high (fix flygym sensor bug or use TetheredWorld; decode descending rates; tune sync). Cost: both halves fit real-time-ish on the test Mac.
   Feasibility 5/10, science 9/10, fun 8/10. This is the one that answers Turaga.

5. "Hermes the fly neuroscientist" — ambitious integrated project (Tier 2/3 + mini)
   Objective: Hermes autonomously runs closed-loop experimental campaigns on the M4 mini host: propose hypothesis (e.g. "MDN activation at >60 Hz suppresses DNa steering gain"), design stimulation protocol, execute, record, analyze, iterate, write up with citations. Bidirectional interface: synthetic sensory injection + spike/motor readouts.
   Effort: high but incremental on top of 2+3+4. Cost: mini-idle-tier.
   Scientific value: methodology demo (agent-driven neuroscience), plus whatever the campaigns find.
   Feasibility 4/10 now → 8/10 after Tier 2 bridge exists.

Ranking by expected value: 1 → 3 → 2 → 4 → 5 (1 and 3 produce real, reproducible numbers immediately; 2 is the toy you'll actually show people; 4 is the science that matters; 5 is the project that makes all of them self-running).

## 9. Scientific limitations (the honest list)

- A connectome gives wiring + predicted neurotransmitter identity. It does NOT give synaptic weights (synapse count is a proxy), receptor types, neuromodulation, neuropeptides, gap junctions, glia, basal firing rates, plasticity, developmental state, or the body (FlyWire is brain-only; the VNC and motor-neuron-to-muscle mapping are not in it). VERIFIED (Shiu limitations).
- Shiu's model: 0 Hz basal firing for every neuron — real brains are not silent. The paper itself names basal-inhibition-dependent and neuromodulatory circuits as failure modes. VERIFIED.
- Signs come from Eckstein et al. 2024 EM-based neurotransmitter prediction (not "sign-of-mass"); prediction errors propagate. REPORTED (DOI 10.1016/j.cell.2024.03.016).
- Behavior in every embodied demo is dominated by the hand-designed/imitation-trained controller; the connectome's causal contribution is unquantified because the random-network control was never run publicly. INFERRED, and the strongest criticism in the field right now.
- "Uploaded a fly" / consciousness framings are not science and are disputed by essentially every connectome researcher quoted in coverage (Turaga, Cowley, Brunton, Tuthill). Eon's own model author says "not a full blown copy." VERIFIED.
- Simulating neural activity (spike patterns in a network) vs reproducing a functioning nervous system (closed-loop, adaptive, embodied behavior generation): the field has done the first at fly scale and only gestures at the second. That gap — not compute — is the frontier. Your Mac can already do the part that works.

## 10. Recommended next action

Approve one decision and I proceed: adopt siliconfly as the daily driver and build the Tier-2 HTTP bridge (Section 7) so Hermes can stimulate neurons and read out populations on the test Mac. Everything needed is already built and verified in ~/.hermes/cache/scratch/drosophila/repos/siliconfly/. The first experiment (Project 1, escape-latency curves) runs entirely on hardware you already own.

Optionally approve the 852 MB flysim data download later if we want its ready-made control plane instead of building our own bridge.

---

## Evidence trail (all paths under ~/.hermes/cache/scratch/drosophila/ unless noted)

- findings/findings-A-repos.md — repo forensics (reconstructed by parent; subagent evidence + direct code verification)
- findings/findings-B-ecosystem.md — ecosystem + credibility, with primary-source URLs and DOIs
- findings/findings-C-hardware.md — Apple Silicon feasibility analysis
- poc/bench.log — NumPy full-scale LIF benchmark (0.10x RT, 0.65 GiB)
- poc/flygym-bench.log + poc/flygym_bench.py — flygym v2.1.1 38.8x RT (sensors-off caveat)
- poc/flybrain-bench.log, repos/fly-brain/data/benchmark-results.csv — Brian2 CPU 0.2568x RT, 1568 spikes (vs Eon Linux 1558)
- repos/siliconfly/ — built binary `SiliconFly`; GPUCHECK PASS; --simtest full diagnostics; peak RSS 250.7 MB
- Key papers: Shiu 2024 (10.1038/s41586-024-07763-9), Dorkenwald 2024 (10.1038/s41586-024-07558-y), Schlegel 2024 (10.1038/s41586-024-07686-5), NeuroMechFly v2 (10.1038/s41592-024-02497-y), Vaxenburg 2025 (10.1038/s41586-025-09029-4), Lappalainen 2024 (10.1038/s41586-024-07939-3), Eckstein 2024 (10.1016/j.cell.2024.03.016), MaleCNS 2026 (10.1016/j.cell.2026.08.015)
- Critiques: theverge.com/ai-artificial-intelligence/894587, thetransmitter.org "digital sphinx", lesswrong.com/posts/ybwcxBRrsKavJB9Wz
