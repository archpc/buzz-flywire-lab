#!/usr/bin/env python3
"""
run_closed_loop.py — closed-loop maze experiment (exploratory; no accepted results).

Closed-loop pipeline per control tick (TICK_MS = 10 sim ms, 100 Hz control):
  1. sense(): 3 whisker ray-casts -> loomL/loomR proximity levels
  2. set_input(): loom levels into the real sensory channels
  3. step(TICK_MS): advance the brain
  4. read rates: dnaL/dnaR EMA population rates
  5. decode: omega = K * (dnaL - dnaR)  [verified sign: away from loom]
  6. agent.move(omega, TICK_MS): rotate + translate + collide/slide

Conditions (identical world, senses, gains, seeds; only the controller differs):
  intact   - brain on intact connectome, loom-driven steering
  shuffled - brain on weights-shuffled connectome (separate bridge, LAB_SHUFFLE)
  ablated  - dnaL+dnaR ablated bridge; decoder reads post-ablation activity
  const    - constant heading (omega=0); same body, same recorded senses
  wallf    - engineered wall-following benchmark (same ray-casts, no brain)

The maze geometry is never given to the brain: only two scalar loom levels go
in; only spike-derived rates come out. No precomputed paths, no planner.
"""

import argparse
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from maze_world import (Maze, Agent, corridor_one_turn, corridor_two_turns,
                        FORWARD_SPEED, MAX_OMEGA)
from neural_bridge import Bridge

TICK_MS = 10
MAX_TICKS = 3000            # 30 s simulated time per episode
STEERING_GAIN_K = 2.0e-3    # rad/ms per DNa spike-count difference (per 10 ms tick)
SEEDS_L1 = [12345, 12346, 12347, 12348, 12349]
SEEDS_HI = [12345, 12346, 12347]


def wall_follow(agent):
    """Engineered benchmark: steer away from the closer side using the same
    ray-casts. NOT part of Buzz's brain."""
    s = agent.sense()
    err = (s["distL"] - s["distR"]) / 1.5          # negative = wall closer left
    omega = 1.5e-4 * err * 200.0                    # rad/ms, bounded below
    return max(-MAX_OMEGA, min(MAX_OMEGA, omega))


def decode(dnaL, dnaR):
    return max(-MAX_OMEGA, min(MAX_OMEGA, STEERING_GAIN_K * (dnaL - dnaR)))


def run_episode(cond, maze, seed, bridge, results_dir, base_name):
    agent = Agent(maze)
    log = []
    outcome = "timeout"
    t_start = time.time()

    if cond == "intact":
        bridge.reset(seed)
        bridge.step(2000)                       # settle
    elif cond in ("shuffled", "ablated"):
        bridge.reset(seed)
        bridge.step(2000)
    elif cond == "const":
        bridge.reset(seed)
        bridge.step(2000)

    for tick in range(MAX_TICKS):
        s = agent.sense()
        if cond in ("intact", "shuffled", "ablated", "const"):
            bridge.set_input(s["loomL"], s["loomR"])
            c = bridge.step_accumulate(TICK_MS)
            dnaL, dnaR = c["dnaL"], c["dnaR"]
            gf, escw, fwd = c["gf"], c["escw"], c["fwd"]
        else:                                   # wallf: no brain
            dnaL = dnaR = gf = escw = fwd = 0.0

        if cond == "intact" or cond == "shuffled" or cond == "ablated":
            omega = decode(dnaL, dnaR)
        elif cond == "const":
            omega = 0.0
        else:
            omega = wall_follow(agent)

        collided = agent.move(omega, dt=TICK_MS)
        log.append({
            "tick": tick, "x": round(agent.x, 4), "y": round(agent.y, 4),
            "heading": round(agent.heading, 4), "loomL": round(s["loomL"], 3),
            "loomR": round(s["loomR"], 3), "dnaL": round(dnaL, 2),
            "dnaR": round(dnaR, 2), "gf": round(gf, 2), "escw": round(escw, 2),
            "omega": round(omega, 6), "collision": collided,
        })
        if agent.at_exit():
            outcome = "reached_exit"
            break

    straight = math.hypot(maze.exit[0] - maze.start[0], maze.exit[1] - maze.start[1])
    episode = {
        "condition": cond, "maze": maze.name, "seed": seed,
        "outcome": outcome, "ticks": len(log), "sim_ms": len(log) * TICK_MS,
        "collisions": agent.collisions,
        "path_len": round(agent.path_len, 3),
        "straight_dist": round(straight, 3),
        "efficiency": round(straight / agent.path_len, 3) if agent.path_len > 0 else None,
        "start": maze.start, "exit": maze.exit,
        "final": [round(agent.x, 4), round(agent.y, 4)],
        "wall_seconds": round(time.time() - t_start, 1),
        "params": {"tick_ms": TICK_MS, "max_ticks": MAX_TICKS,
                   "gain_k": STEERING_GAIN_K, "forward_speed": FORWARD_SPEED,
                   "max_omega": MAX_OMEGA},
        "log": log,
    }
    if results_dir:
        path = os.path.join(results_dir, f"{base_name}.json")
        with open(path, "w") as f:
            json.dump(episode, f)
    return episode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--out", required=True)
    ap.add_argument("--levels", default="1")       # e.g. "1" or "1,2"
    ap.add_argument("--conditions", default="intact,shuffled,ablated,const,wallf")
    ap.add_argument("--seeds", default="")
    ap.add_argument("--label", default="")
    args = ap.parse_args()

    conditions = args.conditions.split(",")
    seeds = [int(s) for s in args.seeds.split(",")] if args.seeds else SEEDS_L1
    levels = [int(x) for x in args.levels.split(",")]

    os.makedirs(os.path.dirname(os.path.expanduser(args.out)), exist_ok=True)
    out_path = os.path.expanduser(args.out)
    results = []
    t0 = time.time()

    bridge = Bridge(args.port) if any(
        c in ("intact", "shuffled", "ablated", "const") for c in conditions) else None
    if bridge:
        st = bridge.status()
        print(f"kernel: n={st['n']} e={st['e']} shuffled={st['shuffled']} "
              f"shuffle_seed={st.get('shuffle_seed')} ablation={st.get('ablation')}")

    if os.path.exists(out_path):
        with open(out_path) as f:
            results = json.load(f)
        done = {(r["condition"], r["maze"], r["seed"]) for r in results}
    else:
        done = set()

    for level in levels:
        for mirror in (False, True):
            for cond in conditions:
                use_bridge = cond in ("intact", "shuffled", "ablated", "const")
                b = bridge if use_bridge else None
                lvl_seeds = seeds if level == 1 else SEEDS_HI
                for seed in lvl_seeds:
                    key = (cond, f"L{level}", seed, mirror)
                    if (cond, f"L{level}{'_mirror' if mirror else ''}", seed) in done:
                        continue
                    maze = corridor_one_turn(mirror) if level == 1 else corridor_two_turns(mirror)
                    ep = run_episode(cond, maze, seed, b, None, "")
                    ep["level"] = level
                    results.append(ep)
                    print(f"L{level}{'M' if mirror else ''} {cond:>8} seed={seed} "
                          f"{ep['outcome']:<12} steps={ep['ticks']:>5} "
                          f"coll={ep['collisions']:>4} eff={ep['efficiency']}")
                    with open(out_path, "w") as f:
                        json.dump(results, f, indent=1)

    summary = {}
    for r in results:
        k = (r["level"], r["maze"], r["condition"])
        s = summary.setdefault(k, {"n": 0, "success": 0, "collisions": 0,
                                   "eff": [], "sim_ms": []})
        s["n"] += 1
        s["success"] += r["outcome"] == "reached_exit"
        s["collisions"] += r["collisions"]
        if r["efficiency"] is not None:
            s["eff"].append(r["efficiency"])
        s["sim_ms"].append(r["sim_ms"])
    print("\n=== SUMMARY ===")
    for k in sorted(summary):
        s = summary[k]
        eff = sum(s["eff"]) / len(s["eff"]) if s["eff"] else None
        print(f"{k}: n={s['n']} success={s['success']} "
              f"mean_collisions={s['collisions']/s['n']:.1f} "
              f"mean_eff={eff and round(eff,3)} mean_sim_s={sum(s['sim_ms'])/s['n']/1000:.1f}")

    with open(out_path, "w") as f:
        json.dump(results, f, indent=1)
    print(f"\n{len(results)} episodes -> {out_path} "
          f"(wall {round(time.time()-t0,1)} s)")


if __name__ == "__main__":
    main()
