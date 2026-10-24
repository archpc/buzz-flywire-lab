#!/usr/bin/env python3
"""
Phase IV analysis: ESCAPE LATENCY LAB.
Reads intact + shuffled datasets, produces latency curves and GF-total plots,
prints the threshold analysis. OBSERVED / MODEL-PREDICTION / BIOLOGICAL-EVIDENCE
categories are kept separate in the report it supports (report_phase2.md).
"""

import json
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.environ.get("BUZZ_HOME", os.path.dirname(os.path.abspath(__file__)))
FIGS = os.path.join(BASE, "figs")
os.makedirs(FIGS, exist_ok=True)


def load(name):
    with open(os.path.join(BASE, "data", name)) as f:
        return json.load(f)


def arm_table(meta):
    """rows: (level, duration) -> list of (latency or None, gf_total) per seed"""
    levels = meta["levels"]
    durations = meta["durations_ms"]
    table = {}
    for t in meta["trials"]:
        key = (round(t["loomL"], 3), t["duration_ms"])
        table.setdefault(key, []).append((t["first_gf_ms"], t["gf_total"]))
    return levels, durations, table


def main():
    intact = load("escape_latency_intact.json")
    shuffled = load("escape_latency_shuffled.json")

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))

    # --- Panel 1: first-spike latency vs loom intensity ---
    ax = axes[0]
    for meta, label, color in [(intact, "intact connectome", "#1f77b4"),
                               (shuffled, "weights-shuffled control", "#d62728")]:
        levels, durations, table = arm_table(meta)
        for dur, mk in zip(durations, ["o", "s"]):
            xs, ys, seed_lats = [], [], []
            for lvl in levels:
                lats = [l for (l, _) in table[(lvl, dur)] if l is not None and l >= 0]
                if lats:
                    xs.append(lvl)
                    ys.append(np.median(lats))
                    seed_lats.append(lats)
            if xs:
                ax.plot(xs, ys, color=color, marker=mk, ms=4,
                        label=f"{label}, {dur} ms")
                # per-seed points, small vertical jitter-free scatter at same x
                for x, lats in zip(xs, seed_lats):
                    ax.scatter([x] * len(lats), lats, s=12, color=color, alpha=0.35,
                               edgecolors="none", zorder=2)
    if not any(l is not None and l >= 0 for (t) in shuffled["trials"] for l in [t["first_gf_ms"]]):
        ax.annotate("shuffled: no GF spikes in any trial\n(latency undefined)",
                    xy=(0.45, 45), fontsize=8, color="#d62728")
    ax.annotate("lines = median over seeds; dots = individual seeds;\no = 100 ms, square = 400 ms",
                xy=(0.38, 12), fontsize=7, color="0.3")
    ax.set_xlabel("loom drive at sensory port (loomL)")
    ax.set_ylabel("GF first-spike latency (ms)")
    ax.set_title("Giant-fiber escape latency")
    ax.set_ylim(0, 60)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # --- Panel 2: total GF spikes vs intensity ---
    ax = axes[1]
    for meta, label, color in [(intact, "intact connectome", "#1f77b4"),
                               (shuffled, "weights-shuffled control", "#d62728")]:
        levels, durations, table = arm_table(meta)
        for dur, ls in zip(durations, ["-", "--"]):
            xs, ys, errs = [], [], []
            for lvl in levels:
                gfs = [g for (_, g) in table[(lvl, dur)]]
                xs.append(lvl)
                ys.append(np.mean(gfs))
                errs.append(np.std(gfs))
            ax.errorbar(xs, ys, yerr=errs, fmt=("o" if ls == "-" else "s"), ls=ls,
                        color=color, ms=4, capsize=3, label=f"{label}, {dur} ms")
    ax.set_xlabel("loom drive at sensory port (loomL)")
    ax.set_ylabel("GF spike count per trial (mean ± sd over seeds)")
    ax.set_title("GF response magnitude")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # --- Panel 3: LC population response (input pathway sanity) ---
    ax = axes[2]
    for meta, label, color in [(intact, "intact connectome", "#1f77b4"),
                               (shuffled, "weights-shuffled control", "#d62728")]:
        levels, durations, table = arm_table(meta)
        for dur, ls in zip(durations, ["-", "--"]):
            xs, ys = [], []
            for lvl in levels:
                rates = [t["lc_rate_post"] for t in meta["trials"]
                         if (round(t["loomL"], 3), t["duration_ms"]) == (lvl, dur)]
                xs.append(lvl)
                ys.append(np.mean(rates))
            ax.plot(xs, ys, ls, color=color, marker="o", ms=4,
                    label=f"{label}, {dur} ms")
    ax.set_xlabel("loom drive at sensory port (loomL)")
    ax.set_ylabel("LC4/LPLC2 rate after trial (Hz)")
    ax.set_title("Looming-detector population response")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    fig.suptitle("Escape Latency Lab — intact vs weights-shuffled connectome "
                 "(3 seeds × 2 durations × 7 intensities)", y=1.02)
    fig.tight_layout()
    p1 = os.path.join(FIGS, "escape_latency_curves.png")
    fig.savefig(p1, dpi=140, bbox_inches="tight")
    print("wrote", p1)

    # --- threshold analysis (console) ---
    print("\n--- response threshold (lowest loomL with GF response in any seed) ---")
    for meta, label in [(intact, "intact"), (shuffled, "shuffled")]:
        levels, durations, table = arm_table(meta)
        for dur in durations:
            thr = None
            for lvl in levels:
                if any(g > 0 for (_, g) in table[(lvl, dur)]):
                    thr = lvl
                    break
            print(f"{label:>8}, {dur:>4} ms: threshold loomL = {thr}")

    # --- seed-spread at near-threshold intensity (0.2) ---
    print("\n--- seed variability at loomL=0.2, 400 ms (latency per seed) ---")
    levels, durations, table = arm_table(intact)
    for (lat, g) in table[(0.2, 400)]:
        print(f"  latency={lat} ms, gf_total={g}")

if __name__ == "__main__":
    main()
