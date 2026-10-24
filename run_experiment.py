#!/usr/bin/env python3
"""
Phase IV Experiment: ESCAPE LATENCY LAB (revised).

Scientific design:
- Uses the kernel's `trial` primitive: the REAL sensory input port (loomL/loomR,
  exactly what the cursor-loom pipeline drives in the app), not direct current
  injection into the looming-detector somas. No answer is wired into the circuit.
- Full recorded window per trial (settle + stimulus + post-stimulus silence);
  no early truncation, so latency CDFs are unbiased.
- Determinism handled honestly: the sim is deterministic per seed, so controlled
  variation comes from (a) stimulus parameters and (b) seeds (different
  per-neuron baseline draws = biologically justified individual variability).
  No invented stochastic variability.
- Controls: no-stim trials interleaved in the same session, plus an identical
  sweep on a weights-shuffled connectome (Shiu-style control, LAB_SHUFFLE=1
  launches the kernel with --shuffle). Group sizes and degree sequences are
  preserved; only wiring specificity is destroyed.

Usage:
  python3 run_experiment.py [--port 8080] [--out data/escape_latency.json]
  Set LAB_SHUFFLE env on the bridge to run the control arm on port 8081.

Hypothesis: looming drive at the sensory port activates the giant fiber with a
short, intensity-dependent latency; the shuffled connectome should lose the
specific loom->GF pathway (markedly higher/absent GF responses).
"""

import json
import os
import sys
import time
import urllib.request

BASE_URL = os.environ.get("LAB_URL", "http://127.0.0.1:8080")

def api(method, path, payload=None):
    data = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path,
        data=data if method == "POST" else None,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())

def run_trial(seed, loomL, duration_ms, settle_ms=2000, post_ms=200):
    """One full trial through the kernel's real-input trial primitive."""
    api("POST", "/reset", {"seed": seed})
    # trial runs settle+stimulus+post in one kernel-side call
    return api("POST", "/trial", {
        "seed": seed,
        "loomL": loomL,
        "loomR": 0.0,
        "duration_ms": duration_ms,
        "settle_ms": settle_ms,
        "post_ms": post_ms,
    })

def summarize(trial):
    lat = trial["first_gf_ms"]
    gf_total = trial["gf_total"]
    lc_stim = sum(trial["loom_counts"][: trial["duration_ms"]])
    return {
        "seed": trial["seed"],
        "loomL": trial["loomL"],
        "duration_ms": trial["duration_ms"],
        "first_gf_ms": lat,
        "gf_total": gf_total,
        "lc_stim_total": lc_stim,
        "lc_rate_post": trial["post_rates"]["loom"],
    }

def main():
    port = 8080
    outfile = (os.path.dirname(os.path.abspath(__file__)) + "/data/escape_latency.json")
    global BASE_URL
    args = sys.argv[1:]
    if "--port" in args:
        port = int(args[args.index("--port") + 1])
        BASE_URL = f"http://127.0.0.1:{port}"
    if "--out" in args:
        outfile = os.path.expanduser(args[args.index("--out") + 1])

    hello = api("GET", "/status")
    shuffled = hello.get("shuffled", False)
    print(f"kernel: n={hello['n']} e={hello['e']} device={hello['device']} "
          f"shuffled={shuffled} shuffle_seed={hello.get('shuffle_seed')}")

    seeds = [12345, 12346, 12347]
    levels = [0.0, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0]   # 0.0 = no-stim control
    durations = [100, 400]

    trials = []
    t0 = time.time()
    for seed in seeds:
        for dur in durations:
            for lvl in levels:
                raw = run_trial(seed, lvl, dur)
                s = summarize(raw)
                s["full"] = raw
                trials.append(s)
                lat = s["first_gf_ms"]
                lat_s = f"{lat:>4}ms" if lat >= 0 else "  none"
                print(f"seed={seed} dur={dur:>4}ms loomL={lvl:.2f} "
                      f"-> GF first {lat_s}, gf_total={s['gf_total']:>3}, "
                      f"lc_rate_post={s['lc_rate_post']:.1f}Hz")

    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    meta = {
        "experiment": "escape_latency_lab",
        "phase": "IV",
        "kernel_version": hello.get("version"),
        "device": hello.get("device"),
        "connectome": {"n": hello["n"], "e": hello["e"]},
        "arm": "shuffled_control" if shuffled else "intact_connectome",
        "shuffle_seed": hello.get("shuffle_seed"),
        "stimulus_port": "loomL/loomR sensory input (trial primitive)",
        "seeds": seeds,
        "levels": levels,
        "durations_ms": durations,
        "settle_ms": 2000,
        "post_ms": 200,
        "wall_seconds": round(time.time() - t0, 2),
        "timestamp": time.time(),
        "trials": trials,
    }
    with open(outfile, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"\nSaved {len(trials)} trials -> {outfile}")

if __name__ == "__main__":
    main()
