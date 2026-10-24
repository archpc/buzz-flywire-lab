---
name: buzz-lab
description: Use when studying fly circuits or the banana experiment.
version: 0.1.0
author: Sein Bunnell (archpc), Hermes Agent
platforms: [macos]
license: MIT
metadata:
  hermes:
    tags: [research, simulation, neuroscience]
---

# Buzz: agent-operated fruit fly connectome lab

## Scope and prerequisites

Use for neural-circuit analysis, controlled stimulation, ablation, reproducibility,
and inspection of the sugar-GRN/MN9 "banana" experiment. Do not force the simulation
into unrelated tasks or treat its output as an authorization or security mechanism.

Repository: https://github.com/archpc/buzz-flywire-lab
Kernel: https://github.com/archpc/siliconfly/tree/lab-bridge

First locate the user's lab checkout. All commands below run from its root, NOT
from this skill directory. Do not assume a particular home-directory path.
Read `docs/INSTALL.md` before building. Requires macOS, Metal, full Xcode, and
Python. The bridge/lifecycle CLI uses only Python's standard library; analysis
needs numpy and matplotlib. Do not install dependencies without permission.

The installed skill is documentation, not an MCP server. Control flows through
the agent's terminal tool to `buzz.py`, localhost HTTP/JSON `lab.py`, JSON-lines
stdin/stdout, and the `SiliconFly --serve` Swift/Metal subprocess.

## Model and limits

FlyWire/FAFB v783: 139,255 neurons, 15,091,983 directed edges representing
54,492,922 synapses. SiliconFly uses a 1 ms LIF model with Q16 fixed-point
synaptic accumulation. Wiring is reconstructed biological data; weights,
neuron dynamics, baseline drives, sensory encodings and calibrated escape
coupling are modelling assumptions, not complete biological measurements.

Historical M5 Pro measurements: 58-59 microseconds per batched simulated ms,
about 17x real time, approximately 250 MB RSS. Do not present these as a new
measurement or a guarantee for another machine.

- No synaptic learning or plasticity. Different seeds are initialization draws,
  not independent biological specimens.
- The desktop body's animation is scripted. Neural firing is not proof of
  embodied behavior, cognition, consciousness, hunger or actual consumption.
- Model responses are not independent biological validation. Separate observed
  simulator output, model predictions, and external biological evidence.

## Lifecycle

```sh
python3 buzz.py start
python3 buzz.py status
python3 buzz.py call GET /status
python3 buzz.py stop
# Separate shuffled-control port; --port is BEFORE the subcommand.
python3 buzz.py --port 8081 start --shuffle 12648430
python3 buzz.py --port 8081 stop
```

`--shuffle` takes decimal integers (12648430 = 0xC0FFEE). Direct bridge
`LAB_SHUFFLE` accepts hex. `BUZZ_HOME` overrides the lifecycle CLI's lab root;
`LAB_BINARY` overrides the bridge's kernel executable.

Bind only to 127.0.0.1. No persistent daemon, LAN exposure or tunnel. Start only
for an authorized task and stop afterward. Check `port_closed` AND
`lingering_pids`; a successful shutdown response alone does not prove cleanup.
The lifecycle wrapper checks `/status` rather than superficial `/` health and
sweeps checkout-specific process patterns because bridge shutdown can hang.
Inspect `logs/bridge-<port>.log` for failures; never silently reuse a different
control arm or shuffle seed.

## Interface

Read `docs/API.md` for the current contract. Main operations:

- GET `/status`: kernel identity, group sizes, initialization and shuffle seeds.
- POST `/reset` with `{"seed":12345}`: recreate simulation state.
- POST `/step` with `{"ms":100}`: advance simulated time.
- POST `/trial`: settle, scalar looming input, post-window; returns GF/loom
  spike series, first GF latency and population rates. Use this for looming
  experiments instead of injecting detector somas and conflating drive classes.
- POST `/stim_trial`: targeted deterministic current or seeded Bernoulli taste
  kicks (discrete-time Poisson approximation); returns watched-neuron spike
  totals, first-spike times and per-step series.
- POST `/set_input`: sensory-port levels for continuous stepping.
- POST `/ablate`, `/ablate_clear`: remove outgoing connectivity and intrinsic
  drive, then restore. This does not prevent spikes from incoming drive.
- GET `/read`: population rates and last-step counts. Do NOT append
  `?last_step=1`: that path returns 404.
- GET `/export`: current snapshot, not a full archived experiment.

## Banana: what was done and how to inspect it

Read `docs/report_phase5.md`, `docs/report_phase6.md`,
`docs/AUDIT-2026-10-24.md` and `data/PROVENANCE.md` before interpreting results.
`run_banana.py` contains the 21 sugar-sensitive GRN root IDs and the MN9 root
720575940660219265 (specimen index 138947). Identity comes from reference
annotations, not a newly discovered neuron class.

Phase V delivered deterministic current to those 21 GRNs for 1,000 ms after
2,000 ms settle, followed by 200 ms post-window. Levels were 0, 0.1, 0.2, 0.3,
0.5. Watch MN9 and the 13 identified pathway interneurons. The banana was not
an image, smell, food object, metabolic reward or a banana-specific encoding.

Historical result: MN9 baseline 19-26 spikes per 1.2 s became 74-87 at strength
0.5. Not strictly monotonic: seed 12347 gives 77 at 0.3 and 74 at 0.5. There
was NO 1.0-strength trial. The shuffled arm was flat at 13-14 spikes; escape
stayed silent. Phase VI added independently seeded taste kicks at 0-400 Hz;
at 200 Hz MN9 counts were 41/31/22 vs baseline 26/23/19. Low-rate responses
were not universally monotonic. Do not smooth away exceptions or imply that
MN9 baseline firing measures stimulus-evoked latency.

The merged `data/banana_peel.json` top-level `shuffle_seed: 0` is misleading.
Its 15 shuffled trials used 0xC0FFEE; use per-trial `arm` and the provenance
sidecar, not that top-level field. Do not rewrite accepted measurements to fix
metadata. Keep errata explicit and dated.

For a permitted verification replay, follow `docs/INSTALL.md` section 4:
reset seed 12345, stimulate the listed GRNs at 0.5, watch MN9 for the same
windows; expected recorded totals are MN9 82 and GF 0. This is a regression
check against a stored trial, not a new biological finding. Do not run even
this replay when the task is read-only.

## Controls and records

- Reset before each arm; preserve identical intervening command sequences.
- Include zero-stimulus controls, weight-shuffled controls, sham ablations and
  relevant cross-circuit checks. Shuffle outcomes form a distribution; one
  shuffle is not a general null result.
- Weight shuffling preserves graph endpoints/degrees and the weight multiset;
  it randomizes weight placement, not graph topology. Neuron relabeling alone
  is not a meaningful control when input roles are relabeled with it.
- Never overwrite `data/*.json` or existing run outputs. Some historical
  runners still default to accepted filenames. Use explicit `--out` where
  supported; otherwise work in a separate copy. Do not run `run_banana.py`
  directly on the accepted data directory merely to inspect an experiment.
- Predeclare sweeps; separate raw JSON from interpretation; record failures.
- For analysis, `analyze_escape.py`, `analyze_ablation.py`, `analyze_mirror.py`
  and `analyze_banana.py` read accepted data and regenerate figures. They
  write `figs/`, so they are not read-only operations.
- After kernel changes, build and run `specimen/SiliconFly --gpucheck`, then
  the relevant circuit/endpoint tests. GPUCHECK validates its numerical
  comparison, not every API path or biological assumption.
- Do not claim maze navigation from the open-loop reflex sequence. Closed-loop
  smoke runs mostly failed; report that separately from accepted circuit work.

## Attribution and publication

Upstream SiliconFly provides the simulator; FlyWire provides the reconstruction;
Shiu et al. provides the scientific model lineage. Hermes agents wrote the lab
code; Sein Bunnell directed, gated and audited the experiments. Preserve that
attribution. Code and this skill are MIT; FlyWire data and the repository's
simulation-derived datasets/figures carry CC BY-NC 4.0 terms. Do not assume
that an MIT skill license grants commercial rights to the connectome data.
