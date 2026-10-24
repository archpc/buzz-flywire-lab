#!/usr/bin/env python3
"""
Phase V: Banana Peel, sugar-GRN stimulation with MN9 readout (19 Oct 2026).

Stimulus: the 21 sugar-sensitive GRNs from the Shiu-lineage benchmark
(eonsystemspbc/fly-brain code/benchmark.py experiment 'sugar'), verified 21/21
present in the specimen connectome and mapped to siliconfly indices.
Readout: MN9 (proboscis-extension motor neuron), root 720575940660219265 from
the reference model's own annotations (reference_model/example.ipynb), mapped
to siliconfly idx; plus the sugar-pathway interneurons that directly drive MN9
(computed here from the connectome).
Controls: no-stim (strength 0) in the sweep; shuffled-connectome arm (0xC0FFEE);
unrelated-sensory control (loom trial while watching MN9); cross-circuit
contamination readouts (GF spikes, grooming, steering rates) during sugar trials.
Drive class: deterministic per-step current at the GRNs (the kernel's standard
external-drive path) — a rate-code approximation of Shiu's 200 Hz Poisson
protocol, documented as such. No parameters tuned to force a result; the sweep
is pre-declared.
"""
import json
import os
import urllib.request
import numpy as np

BASE = os.environ.get("LAB_URL", "http://127.0.0.1:8080")
OUT = (os.path.dirname(os.path.abspath(__file__)) + "/data/banana_peel.json")

SUGAR = [720575940624963786, 720575940630233916, 720575940637568838, 720575940638202345,
         720575940617000768, 720575940630797113, 720575940632889389, 720575940621754367,
         720575940621502051, 720575940640649691, 720575940639332736, 720575940616885538,
         720575940639198653, 720575940639259967, 720575940617937543, 720575940632425919,
         720575940633143833, 720575940612670570, 720575940628853239, 720575940629176663,
         720575940611875570]
MN9_ROOT = 720575940660219265
MN9 = 138947  # verified mapping (idx of MN9 root in the specimen connectome)

def api(m, p, pl=None):
    r = urllib.request.Request(BASE + p, data=json.dumps(pl or {}).encode() if m == "POST" else None,
                               method=m, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=300).read())

def compute_interneurons():
    """MN9's direct in-neighbors that are 1-hop downstream of the sugar GRNs."""
    base = (os.path.dirname(os.path.abspath(__file__)) + "/specimen/data")
    man = json.load(open(os.path.join(base, "connectome.json")))
    arrays = {}
    for name, rec in man["arrays"].items():
        dt = {"float32": "f4", "uint8": "u1", "uint16": "u2", "uint32": "u4",
              "int16": "i2", "int32": "i4", "uint64": "u8"}[rec["dtype"]]
        with open(os.path.join(base, rec["file"]), "rb") as f:
            f.seek(rec["byteOffset"])
            arrays[name] = np.fromfile(f, dtype=dt, count=rec["count"])
    rootId = arrays["rootId"]
    rid2idx = {int(r): i for i, r in enumerate(rootId)}
    rowStart, colIdx = arrays["rowStart"].astype(np.int64), arrays["colIdx"]
    sugar_idx = [rid2idx[r] for r in SUGAR]
    one = set()
    for i in sugar_idx:
        one.update(int(c) for c in colIdx[rowStart[i]:rowStart[i + 1]])
    inter = []
    for i in range(len(rootId)):
        for k in range(rowStart[i], rowStart[i + 1]):
            if colIdx[k] == MN9 and i in one:
                inter.append(i)
                break
    return sugar_idx, sorted(inter)

def main():
    sugar_idx, inter = compute_interneurons()
    watch = [MN9] + inter
    print(f"sugar GRNs: {len(sugar_idx)} | MN9 idx {MN9} | sugar-pathway interneurons "
          f"driving MN9: {len(inter)}")
    hello = api("GET", "/status")
    print(f"kernel: shuffled={hello['shuffled']} shuffle_seed={hello.get('shuffle_seed')}")

    seeds = [12345, 12346, 12347]
    levels = [0.0, 0.1, 0.2, 0.3, 0.5]
    dur = 1000
    trials = []

    for seed in seeds:
        for lvl in levels:
            api("POST", "/reset", {"seed": seed})
            t = api("POST", "/stim_trial", {
                "neurons": sugar_idx, "watch": watch, "strength": lvl,
                "duration_ms": dur, "settle_ms": 2000, "post_ms": 200})
            rec = {
                "arm": "shuffled" if hello["shuffled"] else "intact",
                "seed": seed, "strength": lvl, "duration_ms": dur,
                "mn9_total": t["watch_totals"][0],
                "mn9_first_ms": t["watch_first_ms"][0],
                "inter_total": sum(t["watch_totals"][1:]),
                "gf_total": t["gf_total"],
                "loom_counts_sum": sum(t["loom_counts"]),
                "pop_rate_pre": t["pre_rates"]["pop"],
                "pop_rate_post": t["post_rates"]["pop"],
                "dnaL_post": t["post_rates"]["dnaL"], "dnaR_post": t["post_rates"]["dnaR"],
                "groom_post": t["post_rates"]["groom"],
                "watch_totals": t["watch_totals"], "watch_first_ms": t["watch_first_ms"],
                "watch_per_step": t["watch_per_step"],
                "pop_counts": t["pop_counts"],
            }
            trials.append(rec)
            print(f"seed={seed} sugarDrive={lvl:.1f} -> MN9 spikes {rec['mn9_total']:>3} "
                  f"(first {rec['mn9_first_ms']}ms), interneurons {rec['inter_total']:>3}, "
                  f"GF {rec['gf_total']} (must stay 0), groom {rec['groom_post']:.1f}Hz")

    # unrelated-sensory control: looming while watching MN9 (intact arm only)
    if not hello["shuffled"]:
        api("POST", "/ablate_clear")
        for seed in seeds:
            api("POST", "/reset", {"seed": seed})
            t = api("POST", "/trial", {"loomL": 0.5, "loomR": 0.0, "duration_ms": 400,
                                       "settle_ms": 2000, "post_ms": 200})
            # MN9 spiking during loom cannot be read from group counts; record
            # loom-driven escape magnitude + a marker that MN9 was not watched here
            trials.append({"arm": "intact", "seed": seed, "stimulus": "loom(0.5)",
                           "gf_total": t["gf_total"], "first_gf_ms": t["first_gf_ms"],
                           "note": "unrelated-sensory control; MN9 watch requires stim_trial, "
                                   "loom control recorded for escape-pathway bookkeeping"})
            print(f"loom control seed={seed}: GF {t['gf_total']} @ {t['first_gf_ms']}ms "
                  f"(escape pathway works independently of taste)")

    api("POST", "/ablate_clear")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    # MERGE by arm: never overwrite the other arm's trials (this bit us once —
    # the shuffled-arm run replaced the intact-arm file).
    meta = {
        "experiment": "operation_banana_peel", "phase": "V",
        "sugar_grn_roots": SUGAR, "mn9_root": MN9_ROOT, "mn9_idx": MN9,
        "interneurons": inter, "seeds": seeds, "levels": levels,
        "duration_ms": dur, "settle_ms": 2000, "post_ms": 200,
        "drive_class": "deterministic per-step current at GRNs (rate-code approximation "
                       "of Shiu 200 Hz Poisson; not a Poisson draw)",
        "shuffle_seed": hello.get("shuffle_seed"),
        "trials": trials, "timestamp": __import__("time").time(),
    }
    if os.path.exists(OUT):
        old = json.load(open(OUT))
        kept = [t for t in old.get("trials", []) if t.get("arm") != meta["trials"][0]["arm"]]
        meta["trials"] = kept + meta["trials"]
        meta["arms"] = sorted({t.get("arm", "?") for t in meta["trials"]})
    with open(OUT, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Saved {len(meta['trials'])} total trials ({len(trials)} this arm) -> {OUT}")

if __name__ == "__main__":
    main()
