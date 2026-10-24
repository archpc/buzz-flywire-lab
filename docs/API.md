# SiliconFly Lab Bridge — API

Layered architecture:

```
Hermes / experiment scripts
        │  HTTP/JSON  (127.0.0.1:8080)
        ▼
lab.py  (Python bridge: validation, limits, subprocess lifecycle)
        │  JSON-lines over stdin/stdout  (deterministic, low latency)
        ▼
SiliconFly --serve  (Swift/Metal kernel: Q16 fixed-point LIF, 139,255 neurons)
```

- Bridge binds exclusively to 127.0.0.1. Never exposed via Tailscale or LAN.
- All kernel operations are synchronous and serialized (single command stream);
  GPU work is synchronized by construction.
- Biological time = kernel `sim_ms` (1 ms steps). Wall time = bridge-side clock.
  Both are returned on every response.

## Endpoints (lab.py, port from `LAB_PORT`, default 8080)

| Method | Path       | Body                                   | Returns |
|--------|------------|----------------------------------------|---------|
| GET    | /          | –                                      | 200 OK health |
| GET    | /status    | –                                      | kernel identity: n, e, device, seed, shuffled, group sizes, fixed-point Q |
| POST   | /reset     | `{"seed": <uint32>}`                   | recreates the sim from scratch with the seed → sim_ms=0, total_spikes=0 |
| POST   | /step      | `{"ms": 1..120000}`                    | advances sim; returns sim_ms, total_spikes, avg_step_micros |
| POST   | /stimulate | `{"group": <name>, "strength": 0..2, "duration_ms": 1..5000}` or `{"neurons": [ids], ...}` | optogenetic-style current injection into a population or explicit neurons |
| POST   | /trial     | `{"loomL": 0..1, "loomR": 0..1, "duration_ms": 1..10000, "settle_ms": 0..10000, "post_ms": 0..10000}` | **the real-input trial primitive** (see below) |
| GET    | /read      | – (always includes `last_step`; a query string such as `?last_step=1` is NOT routed and returns 404) | rates (loom/dnaL/dnaR/mdn/fwd/groom/escw/pop), total_spikes, gf_latched, per-step group counts |
| GET    | /export    | –                                      | current read snapshot (raw JSON) |
| POST   | /inject    | `{"neurons": [ids], "amplitude": f}`   | 1 ms current injection (bridge sugar for /stimulate with duration_ms=1) |
| POST   | /ablate    | `{"group": <name>}`, `{"neurons": [ids]}`, or `{"random": N, "seed": s}` (sham) | zero outgoing edges + intrinsic drive of the targets; always derived from the pristine connectome; persists across /reset |
| POST   | /ablate_clear | –                                   | restore the unablated connectome |
| POST   | /set_input | `{"loomL", "loomR", "airPuff", "sugarRate" (0..500 Hz), ...}` | set sensory-port levels; used by closed-loop stepping |
| POST   | /stim_trial | `{"neurons": [ids], "watch": [ids ≤256], "strength": 0..2, "duration_ms", "settle_ms", "post_ms"}` or `{"poisson": true, "rate_hz": 0..500, "watch": [...], ...}` | targeted-neuron (or Poisson taste-port) trial; returns `watch_totals`, `watch_first_ms`, `watch_per_step`, `gf_total`, `pop_counts`, pre/post rates. Out-of-range `rate_hz` → HTTP 400 |
| POST   | /shutdown  | –                                      | stops kernel and bridge (can hang without reaping the kernel; `buzz.py stop` sweeps leftovers) |

Endpoints /ablate through /stim_trial were added in Phases III-VI; this table was updated for publication on 2026-10-24.

## The `trial` primitive (use this for experiments)

Executes settle → stimulus → post-stimulus silence in ONE kernel-side call at
1 ms resolution, and returns the full per-step record:

```json
{"loomL": 0.5, "duration_ms": 400, "settle_ms": 2000, "post_ms": 200}
```

Response fields:
- `first_gf_ms`: first step with a giant-fiber spike after stimulus onset (-1 = none)
- `gf_counts[]`, `loom_counts[]`: per-step spike counts (GF, LC4/LPLC2)
- `pre_rates` / `post_rates`: population-rate EMAs before/after
- `seed`, `shuffled`, `sim_ms`: reproducibility metadata

Why it matters: loomL/loomR are the actual sensory input ports the desktop
app's cursor-loom pipeline drives. `trial` never injects current into the
detector somas, so measured latencies reflect looming processing, not a forced
input. The simtest phase-2 protocol is reproduced exactly.

## Controls

- **No-stim control:** `trial` with `loomL=0, loomR=0` — must produce zero GF spikes.
- **Weights-shuffled control:** launch the bridge with `LAB_SHUFFLE=<seed>`; the
  kernel permutes edge weights (seeded Fisher-Yates LCG) before GPU upload.
  Multiset of weights, degree sequences, group sizes, and fixed-point overflow
  bound are preserved; only wiring specificity is destroyed. This is the
  Shiu-style connectivity-weight shuffle. A neuron relabeling would NOT be a
  valid control (input targeting is role-keyed and would permute too).

## Determinism contract

Same seed + same command sequence ⇒ bit-identical results (Q16 fixed point,
order-independent integer atomics, seed-derived baselines and burst schedule).
`reset` recreates the sim so identical initial conditions are exact.
Variability across "individuals" comes from varying the seed (different
per-neuron baseline draws), never from invented noise.

## Environment variables (bridge)

- `LAB_PORT` (default 8080)
- `LAB_SHUFFLE` (optional; seed for the shuffled-control connectome)
- `LAB_BINARY` (default ./specimen/SiliconFly)

## Limits (enforced bridge-side and kernel-side)

step ≤ 120,000 ms/request; stimulation ≤ 5,000 ms, strength ≤ 2.0; trial ≤
10,000 ms; neuron ids 0 ≤ id < 139,255; membrane read ≤ 4096 neurons/request.
Violations return `{"ok": false, "error": {...}}` — never a crashed fly.
