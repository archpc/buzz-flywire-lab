#!/usr/bin/env python3
"""Phase IV (Mirror Image) analysis figure."""
import json
import os
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

d = json.load(open((os.path.dirname(os.path.abspath(__file__)) + "/data/mirror_image.json")))
agg = defaultdict(list)
for t in d["trials"]:
    agg[(t["condition"], t["side"], t["level"])].append(t)

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Panel 1: GF spike count by condition x side (aggregated over levels/seeds)
ax = axes[0]
conds = ["__intact__", "__sham__", "loomL", "loomR"]
sides = ["L", "R", "B"]
width = 0.25
xs = np.arange(len(conds))
for j, side in enumerate(sides):
    means, errs = [], []
    for c in conds:
        gfs = [t["gf_total"] for t in agg[(c, side, None)] or
               [t for t in d["trials"] if t["condition"] == c and t["side"] == side]]
        means.append(np.mean(gfs))
        errs.append(np.std(gfs))
    ax.bar(xs + (j - 1) * width, means, width, yerr=errs, capsize=3,
           label=f"stimulus {side}")
ax.set_xticks(xs)
ax.set_xticklabels(["intact", "sham(314)", "ablate loomL", "ablate loomR"])
ax.set_ylabel("GF spikes per trial (mean ± sd, 5 seeds × 3 levels)")
ax.set_title("Mirror Image: GF response by condition × stimulus side")
ax.legend(fontsize=8)
ax.grid(alpha=0.3, axis="y")

# Panel 2: shuffled control per side (third shuffle seed)
ax = axes[1]
sh = defaultdict(list)
for t in d["shuffled_control"]["trials"]:
    sh[(t["side"], t["level"])].append(t["gf_total"])
for side, mk, color in [("L", "o", "#1f77b4"), ("R", "s", "#d62728"), ("B", "^", "#7f7f7f")]:
    lv = sorted({k[1] for k in sh})
    ax.plot(lv, [np.mean(sh[(side, l)]) for l in lv], mk + "-", color=color,
            ms=5, label=f"stimulus {side}")
ax.set_xlabel("loom drive level")
ax.set_ylabel("GF spikes per trial (shuffled 0xBAADF00D)")
ax.set_title("Shuffle seed 3: degraded RIGHT-port-only response\n(shuffles 1-2: zero in all 96 trials)")
ax.legend(fontsize=8)
ax.grid(alpha=0.3)

fig.suptitle("Mirror Image — bilateral looming investigation "
             "(5 seeds × 3 levels × 400 ms)", y=1.02)
fig.tight_layout()
out = (os.path.dirname(os.path.abspath(__file__)) + "/figs/mirror_image.png")
fig.savefig(out, dpi=140, bbox_inches="tight")
print("wrote", out)

# asymmetry summary
print("\n=== intact-arm asymmetry summary ===")
for side in sides:
    ts = [t for t in d["trials"] if t["condition"] == "__intact__" and t["side"] == side]
    print(f"stimulus {side}: mean GF {np.mean([t['gf_total'] for t in ts]):.1f}, "
          f"fired {sum(1 for t in ts if t['first_gf_ms']>=0)}/{len(ts)}, "
          f"median latency {np.median([t['first_gf_ms'] for t in ts if t['first_gf_ms']>=0]) if any(t['first_gf_ms']>=0 for t in ts) else 'none'}ms")
l_gf = np.mean([t["gf_total"] for t in d["trials"] if t["condition"] == "__intact__" and t["side"] == "L"])
r_gf = np.mean([t["gf_total"] for t in d["trials"] if t["condition"] == "__intact__" and t["side"] == "R"])
print(f"R/L ratio: {r_gf/l_gf:.2f} (connectome LC->GF |w| ratio: 1053/832 = {1053/832:.2f})")
b_gf = np.mean([t["gf_total"] for t in d["trials"] if t["condition"] == "__intact__" and t["side"] == "B"])
print(f"bilateral additivity: B={b_gf:.1f} vs L+R={l_gf+r_gf:.1f} ({b_gf/(l_gf+r_gf)*100:.0f}%)")
