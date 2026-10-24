# Buzz: agent-operated experiments on a whole-brain fruit fly simulation

Buzz is a localhost lab bench around [SiliconFly](https://github.com/dawsonamf/siliconfly), a
Swift/Metal leaky integrate-and-fire (LIF) simulation of the complete FlyWire adult
*Drosophila* brain. I added an HTTP/JSON control bridge so an AI agent
([Hermes Agent](https://github.com/NousResearch/hermes-agent)) could reset, stimulate, ablate
and record from the simulated brain like an instrument. Then we ran 540 deterministic,
control-matched trials on it.

One of those experiments set out to feed the fly a banana. The fly has no mouth, no gut and
no body, so the "banana" turned out to be current injected into 21 sugar-sensing neurons,
with the proboscis-extension motor neuron as the readout. Section 3 covers what that means
and what it doesn't.

## 1. What is being simulated

| | Source | Status |
|---|---|---|
| Wiring: 139,255 neurons, 15,091,983 edges, 54,492,922 synapses | FlyWire / FAFB v783 (Dorkenwald et al., *Nature* 2024) | biological data (EM reconstruction) |
| Synapse signs | predicted neurotransmitters (Eckstein et al., *Cell* 2024) | ML prediction from EM |
| Neuron model: LIF, 1 ms steps, weight = synapse count × sign | Shiu et al., *Nature* 634:210-219 (2024) | modelling assumption |
| Q16 fixed-point arithmetic, per-neuron baseline drive, hand-tuned giant-fiber gains, calibrated 3 ms escape-latency floor | SiliconFly | simulator assumptions |
| No plasticity, neuromodulation, ventral nerve cord or closed-loop body; the desktop walking animation is scripted | SiliconFly | limitations |

Measured on an M5 Pro MacBook Pro (48 GB), 2026-10-18/19:
- 58-59 µs per simulated ms batched (~17x real time).
- 233-237 µs single-step (~4.3x real time).
- ~250 MB RSS.
- GPU/CPU bit-exact (`--gpucheck`).

For comparison, a naive NumPy event-driven LIF at the same scale ran at 0.10x real time.

The simulation is deterministic: same seed + same command sequence = bit-identical output.
"Individuals" are different seeds, meaning different per-neuron baseline draws. They are not
different flies.

## 2. Architecture

```
agent (terminal tool)  ->  buzz.py  (start/status/call/stop; stdlib)
                       ->  lab.py   (HTTP/JSON, 127.0.0.1 only; validation + limits)
                       ->  JSON-lines over stdin/stdout
                       ->  SiliconFly --serve  (Swift/Metal kernel, specimen/ submodule)
```

This is not an MCP server. The agent discovers Buzz through a Hermes skill and drives it with
plain HTTP from its terminal tool.

- Endpoints: `/status /reset /step /stimulate /inject /trial /stim_trial /set_input /ablate
  /ablate_clear /read /export /shutdown`.
- Every error, from the bridge or the kernel, comes back as HTTP 400 with
  `{"ok": false, "error": {"code", "message"}}`.
- Full contract: [docs/API.md](docs/API.md).

## 3. Experiments (540 accepted trials)

| Phase | Question | Result (model behavior only) | Report |
|---|---|---|---|
| II | Loom → giant-fiber (GF) escape latency | Latency falls monotonically with loom contrast (24-53 ms → 3 ms); zero GF spikes with no stimulus; weight-shuffled connectome: GF never fires (42/42) | [report_phase2](docs/report_phase2.md) |
| III | Ablation battery (14 conditions) | Loom-detector ablation abolishes escape while global rate is preserved (1.71 vs 1.77 Hz); size-matched sham = intact; strictly ipsilateral | [report_phase3](docs/report_phase3.md) |
| IV | Mirror Image (bilateral) | Perfect crossed ablation × side dissociation; right side +23% GF spikes, matching a +27% asymmetry in the connectome's own LC→GF weights; one of three shuffles keeps a weak right-only remnant, so shuffle controls are a distribution | [report_phase4](docs/report_phase4.md) |
| V | **Banana Peel**: drive 21 sugar GRNs, read MN9 | MN9 19-26 → 74-87 spikes/1.2 s (~3.5x); shuffled connectome flat at 13-14; escape stays silent; looming doesn't drive MN9 | [report_phase5](docs/report_phase5.md) |
| VI | Second Helping: Poisson taste port | At Shiu's 200 Hz protocol, 41/31/22 vs baseline 26/23/19; 0 of 3 shuffles respond (escape: 1 of 3) | [report_phase6](docs/report_phase6.md) |

How the banana was implemented:
- Stimulus: the 21 sugar-sensitive gustatory receptor neurons from the Shiu-lineage
  benchmark, all located in v783 by root ID.
- Phase V drive: deterministic current, levels 0-0.5 for 1,000 ms.
- Phase VI drive: Poisson spikes from an independent random stream, so existing modes stay
  bit-identical.
- Readout: MN9 (root 720575940660219265), plus the 13 interneurons connecting the GRNs to MN9.

What it shows: within this model, the sugar → MN9 pathway transmits graded drive, depends on
specific wiring, and is independent of the escape circuit. That is consistent in kind with
the published Shiu et al. result, not an independent prediction.

What it does not show: eating, hunger, preference, satisfaction, cognition or consciousness.
The fly was not fed. A number went up in a motor neuron.

Exploratory, not accepted: a maze experiment (`run_maze.py`, `run_closed_loop.py`, `data/runs/*maze*`).
- The open-loop T-maze scored 10/10, but which side was stimulated already encoded the
  answer. It measures the turn-away reflex, not navigation.
- Closed-loop smoke runs (`data/runs/smoke-maze*.json`) mostly time out with hundreds to
  thousands of wall collisions.
- No conclusions are drawn from either.

## 4. Things that went wrong (and how they were caught)

- `reset()` silently brought ablated neurons back to life by redrawing their baseline drive.
  Fixed by re-applying ablation inside sim recreation; verified across two resets.
- A run script overwrote the intact-arm dataset with the shuffled arm. Re-running reproduced
  every recorded value exactly. The convention since then is immutable run directories.
- A guard that could never fire let `rate_hz: 999` clamp silently to 500 with `ok: true`.
  Now HTTP 400 at both the bridge and kernel layers.
- A compile error was committed before the build check (shell chaining). Caught before any
  data was accepted.
- An earlier trial-ledger summary miscounted. The ledger was recounted from the datasets on disk.
- The publication audit (2026-10-24) found four more issues, listed in
  [docs/AUDIT-2026-10-24.md](docs/AUDIT-2026-10-24.md). Two are report claims the data
  doesn't support, now corrected in place with notes.

## 5. How this was built (attribution)

**Built with Hermes Agent; I directed, gated, and audited.**

- Upstream simulator: SiliconFly by dawsonamf and DenisSergeevitch (MIT).
- Science: FlyWire Consortium (data) and Shiu et al. (model).
- Code: every line in this repo, and the kernel commits on the fork, was written by AI
  agents. Mainly Hermes Agent (model at the time: GLM-5.3-flash), with research subagents for
  the initial survey.
- My part:
  - Set the research questions and the rigor rules: separate *observed* from *model
    prediction* from *biological evidence*, and never mistake a scripted animation for
    emergent behavior.
  - Approved each phase against written conditions.
  - Rejected a shortcut (generic electrical stimulation instead of identified sensory neurons).
  - Required more shuffle seeds (which exposed the shuffle distribution), the Poisson-faithful
    input protocol, and immutable run IDs.
  - Audited the trial ledger.
  - Reviewed the record for this publication.
- Git authorship on the fork is my identity because the agent committed under it. That is
  not a claim of hand-written code.

## 6. Reproduce

See [docs/INSTALL.md](docs/INSTALL.md). Short version:

```sh
git clone --recurse-submodules https://github.com/archpc/buzz-flywire-lab
cd buzz-flywire-lab/specimen
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer ./build.sh
./SiliconFly --gpucheck          # expect GPUCHECK PASS
cd .. && python3 buzz.py start && python3 buzz.py call GET /status && python3 buzz.py stop
```

Requires macOS with Metal and full Xcode. The connectome (~95 MB) ships with upstream SiliconFly.

## Agent skill

The reusable Hermes skill is published at
[skills/buzz-lab/SKILL.md](skills/buzz-lab/SKILL.md). It covers lifecycle,
HTTP tools, controls, the banana protocol, known errata, and provenance.
It contains no private machine paths or roleplay framing. Load it into an
agent's skill library and point the agent at this checkout; the skill itself
contains no executable installation hook and does not start the simulation.

## 7. Layout

- `lab.py`, `buzz.py`, `neural_bridge.py`: bridge, lifecycle CLI, closed-loop client.
- `run_*.py`, `analyze_*.py`: experiments and analysis (numpy + matplotlib).
- `data/`: raw trial records. Accepted datasets are immutable and copied verbatim; metadata
  corrections (shuffle seeds per dataset) live in [data/PROVENANCE.md](data/PROVENANCE.md).
- `data/runs/`: per-session runs.
- `figs/`: figures regenerated from `data/` by the `analyze_*.py` scripts.
- `docs/`: phase reports, API, install, integration notes, gustatory design doc, audit.
- `specimen/`: submodule → [archpc/siliconfly@lab-bridge](https://github.com/archpc/siliconfly/tree/lab-bridge),
  7 commits on upstream `8839d84`.

Reports cite local commit hashes. The published fork has the same trees under new hashes,
because only author identity was rewritten:

| report | fork | change |
|---|---|---|
| 179dd61 | 96449e7 | headless JSON-lines lab server + weights-shuffle control |
| 0bbf9e5 | 56b134f | Makefile build/test/serve |
| 64c3f79 | 5b0bc00 | ablation primitive + sham; ablation survives reset |
| 1ab55ff | b380835 | stim_trial primitive |
| cf0bf7e | ac77d31 | stim_trial compile fix |
| 3d7f130 | 40bc5f0 | Poisson taste port (inputKind 5, independent PCG stream) |
| f16e990 | 3918f44 | rate_hz validated instead of clamped |

## 8. Licenses

- Code in this repo: MIT ([LICENSE](LICENSE)).
- Kernel fork: MIT (upstream).
- FlyWire connectome data: CC BY-NC 4.0. `data/` and `figs/` are derived from simulations on
  that data and are released under CC BY-NC 4.0 with attribution to the FlyWire Consortium
  (Dorkenwald et al. 2024; Schlegel et al. 2024).
