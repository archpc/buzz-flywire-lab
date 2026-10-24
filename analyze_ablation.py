#!/usr/bin/env python3
"""Phase III analysis: ablation battery figure + summary."""
import json
import os
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

d = json.load(open((os.path.dirname(os.path.abspath(__file__)) + "/data/ablation_battery.json")))
agg = defaultdict(list)
for t in d["trials"]:
    agg[t["condition"]].append(t)

order = ["__intact__", "__sham__", "loom", "loomL", "loomR", "sens", "gf",
         "ascend", "dnaL", "dnaR", "mdn", "fwd", "groom", "escw"]
labels = ["intact", "sham(314)", "loom", "loomL", "loomR", "sens", "gf",
          "ascend", "dnaL", "dnaR", "mdn", "fwd", "groom", "escw"]
intact_mean = np.mean([t["gf_total"] for t in agg["__intact__"]])

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

ax = axes[0]
means, errs = [], []
for c in order:
    gfs = [t["gf_total"] for t in agg[c]]
    means.append(np.mean(gfs))
    errs.append(np.std(gfs))
colors = ["#2ca02c" if abs(m - intact_mean) < 5 else "#d62728" for m in means]
ax.bar(range(len(order)), means, yerr=errs, color=colors, capsize=3)
ax.axhline(intact_mean, color="0.4", ls="--", lw=1, label=f"intact baseline {intact_mean:.1f}")
for i, m in enumerate(means):
    if m == 0:
        ax.scatter([i], [0], marker="x", s=90, color="#d62728", zorder=5, linewidths=2)
        ax.annotate("0\n(abolished)", xy=(i, 3), ha="center", fontsize=8, color="#d62728")
ax.set_xticks(range(len(order)))
ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
ax.set_ylabel("GF spike count per trial (mean ± sd, 3 seeds × 3 levels)")
ax.set_title("Ablation battery: GF response retention\n(green = intact-level, red = abolished)")
ax.legend(fontsize=8)
ax.grid(alpha=0.3, axis="y")

ax = axes[1]
offsets = {"__intact__": -0.06, "__sham__": -0.02, "loom": 0.02, "loomL": 0.06, "sens": 0.10}
for c, mk, color in [("__intact__", "o", "#2ca02c"), ("__sham__", "s", "#7f7f7f"),
                     ("loom", "^", "#d62728"), ("loomL", "v", "#ff7f0e"),
                     ("sens", "D", "#1f77b4")]:
    xs, ys, es = defaultdict(list), [], []
    for t in agg[c]:
        xs[t["loomL"]].append(t["gf_total"])
    lv = sorted(xs)
    off = offsets.get(c, 0.0)
    ax.errorbar([l + off for l in lv], [np.mean(xs[l]) for l in lv],
                yerr=[np.std(xs[l]) for l in lv],
                fmt=mk + "-", color=color, ms=5, capsize=3, label=c.strip("_"))
ax.set_xlabel("loom drive (loomL)")
ax.set_ylabel("GF spikes per trial")
ax.set_title("Dose-response under ablation")
ax.legend(fontsize=8)
ax.grid(alpha=0.3)

fig.suptitle("Phase III ablation battery — intact vs sham vs circuit ablations "
             "(looming stimulus at left sensory port)", y=1.02)
fig.tight_layout()
out = (os.path.dirname(os.path.abspath(__file__)) + "/figs/ablation_battery.png")
fig.savefig(out, dpi=140, bbox_inches="tight")
print("wrote", out)

print(f"\n{'condition':>10} | {'GF fire':>7} | {'med lat':>7} | {'mean gf':>7} | {'pop_pre':>7} | verdict")
print("-" * 78)
for c, lab in zip(order, labels):
    ts = agg[c]
    fired = sum(1 for t in ts if t["first_gf_ms"] >= 0)
    lats = sorted(t["first_gf_ms"] for t in ts if t["first_gf_ms"] >= 0)
    med = f"{lats[len(lats)//2]}ms" if lats else "none"
    gf = np.mean([t["gf_total"] for t in ts])
    pop = np.mean([t["pop_rate_pre"] for t in ts])
    if abs(gf - intact_mean) < 5:
        verdict = "no effect (negative finding)"
    elif gf == 0:
        verdict = "escape abolished"
    else:
        verdict = "partial effect"
    print(f"{lab:>10} | {fired:>4}/9 | {med:>7} | {gf:>7.1f} | {pop:>7.2f} | {verdict}")
