#!/usr/bin/env python3
"""Phase V analysis: sugar dose-response, MN9 readout, controls."""
import json
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

d = json.load(open((os.path.dirname(os.path.abspath(__file__)) + "/data/banana_peel.json")))
sugar = [t for t in d["trials"] if "strength" in t]
loom_ctl = [t for t in d["trials"] if t.get("stimulus", "").startswith("loomL")]

fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))

ax = axes[0]
for arm, color, mk in [("intact", "#2ca02c", "o"), ("shuffled", "#d62728", "s")]:
    xs, ys, errs = [], [], []
    for lvl in d["levels"]:
        ts = [t for t in sugar if t["arm"] == arm and t["strength"] == lvl]
        if ts:
            xs.append(lvl)
            ys.append(np.mean([t["mn9_total"] for t in ts]))
            errs.append(np.std([t["mn9_total"] for t in ts]))
    ax.errorbar(xs, ys, yerr=errs, fmt=mk + "-", color=color, ms=5, capsize=3,
                label=f"{arm} connectome")
for seed, mk in [(12345, "v"), (12346, "^"), (12347, "<")]:
    ts = [t for t in sugar if t["arm"] == "intact" and t["seed"] == seed]
    ax.plot([t["strength"] for t in ts], [t["mn9_total"] for t in ts],
            mk + "--", color="#2ca02c", ms=4, alpha=0.45, lw=0.8)
ax.set_xlabel("sugar drive at the 21 GRNs (deterministic rate-code)")
ax.set_ylabel("MN9 spikes per 1.2 s trial")
ax.set_title("MN9 feeding-motor-neuron response to sugar drive\n"
             "(dashed: individual seeds; shuffled arm: flat null)")
ax.legend(fontsize=8)
ax.grid(alpha=0.3)

ax = axes[1]
labels, gf_vals, mn9_vals = [], [], []
for lvl in d["levels"]:
    ts = [t for t in sugar if t["arm"] == "intact" and t["strength"] == lvl]
    labels.append(f"sugar\n{lvl}")
    gf_vals.append(np.mean([t["gf_total"] for t in ts]))
    mn9_vals.append(np.mean([t["mn9_total"] for t in ts]))
labels.append("loomL\ndrive 0.3")
gf_vals.append(np.mean([t["gf_total"] for t in loom_ctl]))
mn9_vals.append(np.mean([t["mn9_total"] for t in loom_ctl]))
x = np.arange(len(labels))
ax.bar(x - 0.2, gf_vals, 0.4, color="#d62728", label="GF spikes (escape)")
ax.bar(x + 0.2, mn9_vals, 0.4, color="#1f77b4", label="MN9 spikes (feeding)")
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=8)
ax.set_ylabel("spikes per trial (mean over 3 seeds)")
ax.set_title("Cross-circuit dissociation\ntaste -> MN9 only; looming -> GF only")
ax.legend(fontsize=8)
ax.grid(alpha=0.3, axis="y")

fig.suptitle("Banana Peel — reconstructed feeding circuit under sugar drive", y=1.02)
fig.tight_layout()
out = (os.path.dirname(os.path.abspath(__file__)) + "/figs/banana_peel.png")
fig.savefig(out, dpi=140, bbox_inches="tight")
print("wrote", out)

print("\n=== intact-arm MN9 dose-response (spikes per 1.2 s trial) ===")
for lvl in d["levels"]:
    ts = [t for t in sugar if t["arm"] == "intact" and t["strength"] == lvl]
    vals = [t["mn9_total"] for t in ts]
    lat = [t["mn9_first_ms"] for t in ts]
    print(f"sugarDrive {lvl}: MN9 {vals} (first-spike {lat} ms), "
          f"interneurons {[t['inter_total'] for t in ts]}, GF {[t['gf_total'] for t in ts]}")
print("\n=== shuffled arm (0xC0FFEE) MN9: flat null ===")
for lvl in d["levels"]:
    ts = [t for t in sugar if t["arm"] == "shuffled" and t["strength"] == lvl]
    print(f"sugarDrive {lvl}: MN9 {[t['mn9_total'] for t in ts]}")
print("\n=== loom control (MN9 watched) ===")
for t in loom_ctl:
    print(f"seed {t['seed']}: MN9 {t['mn9_total']} spikes, GF {t['gf_total']} spikes "
          f"(first at {t['gf_first_ms']} ms)")
