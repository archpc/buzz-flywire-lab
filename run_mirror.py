#!/usr/bin/env python3
"""
Phase IV: Mirror Image (approved 19 Oct 2026).

Closes the lateralization question from Phase III. Design requirements:
1. Left, right, and bilateral sensory stimulation tested independently.
2. Mirrored ablations: ablate:loomL and ablate:loomR repeated under all three
   stimulus sides (always derived from the pristine connectome).
3. Controls: intact baseline + size-matched sham (314 'other', seed 7) on the
   intact connectome; third independent shuffled-network seed (0xBAADF00D on
   port 8081, intact-only sweep) joins 0xC0FFEE and 0xDEADBE0F.
4. 5 initialization seeds (12345-12349): independent network realizations, not
   repeated trials from one seed.
5. Metrics: GF first-spike latency, GF spike counts, DNa L/R rates (steering
   laterality), LC rates, population rates (direct-vs-global separation).
6. All original simulation parameters preserved; per-trial raw records saved.

Matrix: 4 conditions x 3 stimulus sides x 3 levels x 5 seeds = 180 trials
(intact connectome) + 45 shuffled-control trials = 225 total.
"""
import json
import os
import time
import urllib.request

BASE_URL = os.environ.get("LAB_URL", "http://127.0.0.1:8080")
OUT = (os.path.dirname(os.path.abspath(__file__)) + "/data/mirror_image.json")

def api(m, p, pl=None):
    r = urllib.request.Request(BASE_URL + p, data=json.dumps(pl or {}).encode() if m == "POST" else None,
                               method=m, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=300).read())

SEEDS = [12345, 12346, 12347, 12348, 12349]
LEVELS = [0.4, 0.7, 1.0]
SIDES = {"L": (1, 0), "R": (0, 1), "B": (1, 1)}
CONDITIONS = ["__intact__", "__sham__", "loomL", "loomR"]
DUR = 400

def set_condition(cond):
    if cond == "__intact__":
        api("POST", "/ablate_clear")
        return "intact"
    if cond == "__sham__":
        return api("POST", "/ablate", {"random": 314, "seed": 7})["ablation"]
    return api("POST", "/ablate", {"group": cond})["ablation"]

def main():
    hello = api("GET", "/status")
    shuffled = hello["shuffled"]
    print(f"kernel: n={hello['n']} shuffled={shuffled} shuffle_seed={hello.get('shuffle_seed')}")

    trials = []
    t0 = time.time()
    for cond in CONDITIONS:
        desc = set_condition(cond)
        for seed in SEEDS:
            for side, (ll, lr_scale) in SIDES.items():
                for lvl in LEVELS:
                    api("POST", "/reset", {"seed": seed})
                    t = api("POST", "/trial", {
                        "loomL": lvl * ll, "loomR": lvl * lr_scale,
                        "duration_ms": DUR, "settle_ms": 2000, "post_ms": 200})
                    rec = {
                        "condition": cond, "ablation": desc, "seed": seed,
                        "side": side, "loomL": round(lvl * ll, 3),
                        "loomR": round(lvl * lr_scale, 3), "level": lvl,
                        "duration_ms": DUR,
                        "first_gf_ms": t["first_gf_ms"], "gf_total": t["gf_total"],
                        "lc_rate_post": t["post_rates"]["loom"],
                        "dnaL_rate_post": t["post_rates"]["dnaL"],
                        "dnaR_rate_post": t["post_rates"]["dnaR"],
                        "pop_rate_pre": t["pre_rates"]["pop"],
                        "pop_rate_post": t["post_rates"]["pop"],
                    }
                    trials.append(rec)
                    lat = rec["first_gf_ms"]
                    lat_s = f"{lat:>3}ms" if lat >= 0 else "none"
                    print(f"{cond:>9} seed={seed} side={side} lvl={lvl:.1f} "
                          f"-> GF {lat_s:>4} gf={rec['gf_total']:>3} "
                          f"dnaL/R={rec['dnaL_rate_post']:.0f}/{rec['dnaR_rate_post']:.0f}")

    api("POST", "/ablate_clear")
    print("baseline restored (ablate_clear)")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    meta = {
        "experiment": "operation_mirror_image", "phase": "IV",
        "conditions": CONDITIONS, "sides": list(SIDES), "levels": LEVELS,
        "seeds": SEEDS, "duration_ms": DUR, "settle_ms": 2000, "post_ms": 200,
        "sham": {"size": 314, "seed": 7},
        "shuffle_seed": hello.get("shuffle_seed"), "shuffled": shuffled,
        "wall_seconds": round(time.time() - t0, 1), "timestamp": time.time(),
        "trials": trials,
    }
    with open(OUT, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Saved {len(trials)} trials -> {OUT}")

if __name__ == "__main__":
    main()
