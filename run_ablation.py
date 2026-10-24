#!/usr/bin/env python3
"""
Phase III: ABLATION BATTERY (19 Oct 2026).

Command conditions, executed exactly as ordered:
- Baseline responses established FIRST (intact connectome).
- One population ablated at a time (kernel always derives from the pristine
  connectome; ablations never compound; ablate_clear restores baseline exactly).
- Sham control: random size-matched slice of the unannotated 'other' population.
- A second shuffled-network seed (0xDEADBE0F) joins Phase IV's 0xC0FFEE to put
  a spread on the control arm.
- Records GF latency + spike counts AND whole-population rates, so direct
  circuit effects are separated from changes in global network activity.
- Negative findings are recorded, not hidden.

Conditions: intact, sham(314), gf, loom, loomL, loomR, sens, ascend,
dnaL, dnaR, mdn, fwd, groom, escw.
Per condition: 3 seeds x 3 loom levels (0.4/0.7/1.0) x 400 ms stimulus.
"""
import json
import os
import time
import urllib.request

BASE_URL = os.environ.get("LAB_URL", "http://127.0.0.1:8080")
OUT = (os.path.dirname(os.path.abspath(__file__)) + "/data/ablation_battery.json")

def api(method, path, payload=None):
    data = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(BASE_URL + path, data=data if method == "POST" else None,
                                 method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read())

SEEDS = [12345, 12346, 12347]
LEVELS = [0.4, 0.7, 1.0]
DUR = 400
CONDITIONS = ["__intact__", "__sham__", "gf", "loom", "loomL", "loomR",
              "sens", "ascend", "dnaL", "dnaR", "mdn", "fwd", "groom", "escw"]
SHAM_SIZE = 314  # = loomL(162) + loomR(152); size-matched sham
SHAM_SEED = 7

def set_condition(cond):
    if cond == "__intact__":
        api("POST", "/ablate_clear")
        return "intact"
    if cond == "__sham__":
        r = api("POST", "/ablate", {"random": SHAM_SIZE, "seed": SHAM_SEED})
        return r["ablation"]
    r = api("POST", "/ablate", {"group": cond})
    return r["ablation"]

def main():
    hello = api("GET", "/status")
    print(f"kernel: n={hello['n']} e={hello['e']} shuffled={hello['shuffled']} "
          f"shuffle_seed={hello.get('shuffle_seed')}")

    trials = []
    t0 = time.time()
    for cond in CONDITIONS:
        desc = set_condition(cond)
        for seed in SEEDS:
            for lvl in LEVELS:
                api("POST", "/reset", {"seed": seed})
                t = api("POST", "/trial", {"loomL": lvl, "loomR": 0.0,
                                           "duration_ms": DUR,
                                           "settle_ms": 2000, "post_ms": 200})
                rec = {
                    "condition": cond, "ablation": desc, "seed": seed,
                    "loomL": round(lvl, 3), "duration_ms": DUR,
                    "first_gf_ms": t["first_gf_ms"], "gf_total": t["gf_total"],
                    "lc_rate_post": t["post_rates"]["loom"],
                    "pop_rate_pre": t["pre_rates"]["pop"],
                    "pop_rate_post": t["post_rates"]["pop"],
                }
                trials.append(rec)
                lat = rec["first_gf_ms"]
                lat_s = f"{lat:>4}ms" if lat >= 0 else " none"
                print(f"{cond:>10} seed={seed} lvl={lvl:.1f} -> GF{lat_s} "
                      f"gf={rec['gf_total']:>3} pop_pre={rec['pop_rate_pre']:.2f} "
                      f"pop_post={rec['pop_rate_post']:.2f}")

    # restore pristine baseline before leaving, as ordered
    api("POST", "/ablate_clear")
    print("baseline restored (ablate_clear) — Buzz is whole again")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    meta = {
        "experiment": "ablation_battery", "phase": "III",
        "conditions": CONDITIONS, "sham": {"size": SHAM_SIZE, "seed": SHAM_SEED},
        "seeds": SEEDS, "levels": LEVELS, "duration_ms": DUR,
        "settle_ms": 2000, "post_ms": 200,
        "shuffle_seed": hello.get("shuffle_seed"), "shuffled": hello["shuffled"],
        "wall_seconds": round(time.time() - t0, 1), "timestamp": time.time(),
        "trials": trials,
    }
    with open(OUT, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Saved {len(trials)} trials -> {OUT}")

if __name__ == "__main__":
    main()
