# Buzz in Hermes — integration record

Date: 2026-10-19. Operator: Hermes Agent.

## Where Buzz lives

- **Kernel**: `specimen/SiliconFly` (Swift/Metal, Q16 LIF over FlyWire v783,
  139,255 neurons). Canonical checkout: `specimen/` (git).
  Upstream clone: `siliconfly/`.
- **Bridge**: `lab.py` — HTTP/JSON on 127.0.0.1:8080 (stdlib),
  JSON-lines to the kernel subprocess. Contract: `API.md`.
- **Lifecycle CLI**: `buzz.py` (stdlib, ~200 lines) — start /
  status / call / stop. This is the only new code added by the integration.
- **Hermes-side**: skill `research/buzz-lab` in `~/.hermes/skills/` —
  capabilities, limitations, lifecycle recipes, data conventions. That is the
  discovery mechanism: any session that scans skills finds Buzz.

## Why this mechanism

Simplest maintainable option. The bridge already is the control interface;
a skill + 200-line lifecycle wrapper adds on-demand operation without a new
framework, MCP server, or daemon. Hermes invokes Buzz through the standard
terminal tool — same convention as every other local capability.

## On-demand lifecycle

- `buzz start` reuses a healthy instance, spawns otherwise, and detects a
  kernel-dead bridge (health is checked against `/status`, not `/` — a
  bridge whose kernel died still serves `/`). Stale bridges on the port are
  evicted before respawn.
- `buzz stop` posts `/shutdown`, then sweeps lingering processes: observed
  failure mode is the bridge closing its listener while hanging without
  reaping the kernel child. Verified by `pgrep`, not port state.
- No daemon, no LaunchAgent, no persistent service. The fly lives exactly as
  long as the experiment session.

## Experiment records

- Accepted datasets: `data/*.json` — immutable, never overwritten.
- Session outputs: `data/runs/<UTCts>-<slug>/` via `--out`.
- Reports: `REPORT.md`, `report_phase2..6.md`; figures in `figs/`.
- Raw measurements (JSON) are kept separate from interpretation (markdown).
- Reference/provenance data: `reference_model/` (FlyWire v783 + Shiu
  notebook) — read-only.
- Retrieval through Hermes' file tools (search_files / read_file) against
  ``; datasets are not copied into Hermes memory.

## Validation performed (2026-10-19)

- `./SiliconFly --gpucheck` → GPUCHECK PASS (9.9 s).
- `./SiliconFly --simtest` → PASS (GF silent at rest, fires on loom;
  locomotor drive fluctuates; siesta alive; 59 µs/step batched).
- `buzz start` → n=139255, e=15091983, device "Apple M5 Pro".
- Determinism: seed 12345, trial(loomL=0.5, 400 ms) twice after reset →
  bit-identical JSON (sha256 match, first_gf_ms=5, gf_total=40). Also
  reproduced identically across a full bridge restart.
- Validated experiment re-run: `run_experiment.py` escape-latency sweep,
  42 trials → `data/runs/20261019t-integration-check/` (no accepted dataset
  touched). No-stim control: zero GF spikes; latency falls monotonically
  with loom contrast (3→5 ms at high contrast), matching accepted baseline.
- Failure recovery: SIGKILL bridge → `buzz start` respawns clean; SIGKILL
  kernel (bridge alive) → detected via `/status`, zombie evicted, respawn
  verified with a reproduced trial.
- Clean shutdown: `buzz stop` → port closed, `lingering_pids: []`.
- Scope: no Hermes config changes, no global services, no new dependencies.

## Known limitations

- `/shutdown` in lab.py can hang without reaping the kernel; `buzz stop`
  compensates. A lab.py fix (reap + exit) would be cleaner but is left to a
  separate change so the original bridge stays the verified baseline.
- `run_experiment.py` defaults `--out` into `data/` — agents must pass an
  explicit `--out` under `data/runs/` (convention documented in the skill).
- Determinism is per-kernel-process-state: commands issued between reset and
  the measured sequence must be identical across runs being compared.
