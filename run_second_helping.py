#!/usr/bin/env python3
"""
Phase VI: Second Helping (19 Oct 2026).

Objectives:
1-3. Additional independently shuffled connectomes vs the feeding circuit;
     quantify the distribution of randomized-network responses; compare intact.
4. Deterministic guarantees preserved: GPUCHECK + simtest re-verified after the
   kernel change; the taste-off path is bit-identical (independent RNG stream).
5. Poisson-faithful gustatory input: new kernel taste port (inputKind 5,
   per-step Bernoulli at rate_hz with an independent PCG stream seeded from the
   sim seed). Deterministic-per-seed and reproducible, unlike ad-hoc scripts.
6. Testable predictions recorded in the report.

DATA-INTEGRITY CONVENTION (mandatory): every run writes to
its own immutable directory data/runs/<run_id>/; existing accepted datasets are
never opened for writing. run_id is recorded inside every result file.
"""
import json
import os
import time
import urllib.request

RUN_ID = time.strftime("202610%dt%H%M%S").replace(":", "").lower() + "-second-helping"
RUN_DIR = (os.path.dirname(os.path.abspath(__file__)) + f"/data/runs/{RUN_ID}")
os.makedirs(RUN_DIR, exist_ok=True)
MN9 = 138947

def api(base, m, p, pl=None):
    r = urllib.request.Request(base + p, data=json.dumps(pl or {}).encode() if m == "POST" else None,
                               method=m, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=300).read())

SEEDS = [12345, 12346, 12347]
DET_LEVELS = [0.0, 0.1, 0.2, 0.3, 0.5]
POISSON_RATES = [0, 50, 100, 200, 400]
DUR = 1000

def sugar_sweep(base, arm, mode="det", levels=None):
    levels = levels or DET_LEVELS
    hello = api(base, "GET", "/status")
    out = []
    for seed in SEEDS:
        for lvl in levels:
            api(base, "POST", "/reset", {"seed": seed})
            if mode == "det":
                t = api(base, "POST", "/stim_trial", {
                    "poisson": False, "neurons": SUGAR_IDX, "watch": [MN9],
                    "strength": lvl, "duration_ms": DUR, "settle_ms": 2000, "post_ms": 200})
                param = {"strength": lvl}
            else:
                t = api(base, "POST", "/stim_trial", {
                    "poisson": True, "rate_hz": lvl, "watch": [MN9],
                    "duration_ms": DUR, "settle_ms": 2000, "post_ms": 200})
                param = {"rate_hz": lvl}
            rec = {
                "arm": arm, "mode": mode, "seed": seed, **param,
                "duration_ms": DUR,
                "mn9_total": t["watch_totals"][0], "mn9_first_ms": t["watch_first_ms"][0],
                "gf_total": t["gf_total"],
                "pop_rate_post": t["post_rates"]["pop"],
            }
            out.append(rec)
            print(f"[{arm}/{mode}] seed={seed} lvl={lvl} -> MN9 {rec['mn9_total']:>3} "
                  f"(first {rec['mn9_first_ms']:>3}ms), GF {rec['gf_total']}")
    return out

def slope(rows, xkey):
    """least-squares slope of MN9 total vs drive level"""
    xs = [r[xkey] for r in rows]
    ys = [r["mn9_total"] for r in rows]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    return num / den if den else 0.0

SUGAR_IDX = [69416, 98045, 123346, 124845, 29414, 101067, 110984, 51345, 49815,
             130314, 127443, 28958, 127169, 127322, 33003, 108934, 111872,
             14903, 91001, 92717, 12549]

def main():
    arms = [
        ("intact", "http://127.0.0.1:8080", None),
        ("shuffle-0xC0FFEE", "http://127.0.0.1:8081", "0xC0FFEE"),
        ("shuffle-0xFEEDF00D", "http://127.0.0.1:8082", "0xFEEDF00D"),
        ("shuffle-0x8BADF00D", "http://127.0.0.1:8083", "0x8BADF00D"),
    ]
    all_trials = []
    t0 = time.time()
    for arm, base, shuffle_seed in arms:
        hello = api(base, "GET", "/status")
        assert hello["shuffled"] == (shuffle_seed is not None), f"{arm}: wrong kernel"
        # deterministic-mode sweep on the two NEW shuffle arms only (intact and
        # 0xC0FFEE deterministic sweeps already exist in Phase V records)
        if shuffle_seed in ("0xFEEDF00D", "0x8BADF00D"):
            all_trials += sugar_sweep(base, arm, "det")
        # Poisson sweep on intact and 0xC0FFEE (feeding-circuit null check under
        # the faithful protocol), plus the new arms for the distribution
        if arm == "intact" or shuffle_seed == "0xC0FFEE":
            all_trials += sugar_sweep(base, arm, "poisson", POISSON_RATES)

    # per-arm/per-mode slopes
    from collections import defaultdict
    groups = defaultdict(list)
    for t in all_trials:
        groups[(t["arm"], t["mode"])].append(t)
    slopes = {f"{a}/{m}": round(slope(g, "strength" if m == "det" else "rate_hz"), 1)
              for (a, m), g in groups.items()}

    meta = {
        "run_id": RUN_ID, "experiment": "operation_second_helping", "phase": "VI",
        "sweeps": {"det_levels": DET_LEVELS, "poisson_rates_hz": POISSON_RATES,
                   "seeds": SEEDS, "duration_ms": DUR},
        "mn9_idx": MN9,
        "slopes_mn9_per_unit": slopes,
        "wall_seconds": round(time.time() - t0, 1),
        "trials": all_trials,
    }
    out = os.path.join(RUN_DIR, "results.json")
    with open(out, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"\nimmutable run dir: {RUN_DIR}")
    print("MN9 response slopes:", json.dumps(slopes, indent=2))

if __name__ == "__main__":
    main()
