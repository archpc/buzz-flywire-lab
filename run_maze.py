#!/usr/bin/env python3
"""
MAZE NAVIGATION VIA HARDWIRED THREAT AVOIDANCE (Phase V).

Design (pre-declared before running):
- The simulated fly cannot learn. The claim tested here is narrower: the
  hardwired looming-escape circuit can solve a T-maze when the blocked
  corridor is signaled by a looming stimulus on that side.
- Maze: J=10 sequential T-junctions. At each junction the WRONG side's wall
  looms (level 0.8, 400 ms). Decision rule: dominant descending-command side
  during the stimulus window is the turn (loomL -> dnaR dominance -> turn
  right, i.e. AWAY from the threat; verified in the lateralization probe).
  Correct turn = side opposite the loom. Ties count as no-decision.
- Continuous session per seed: no reset between junctions; 600 ms refractory
  settle after each decision so stimulus-window counts are clean and state
  carryover is part of the measured behavior. Deterministic per seed.
- Arms: intact connectome seeds [12345..12347], no-stim control (identical
  procedure, loom=0; argmax decisions are drift, expect ~chance), and a
  weights-shuffled connectome arm on a second bridge (LAB_SHUFFLE=1).

Usage:
  python3 run_maze.py --port 8080 --out data/runs/<ts>-maze/intact.json
  python3 run_maze.py --port 8081 --out data/runs/<ts>-maze/shuffled.json --label shuffled
  python3 run_maze.py --port 8080 --out data/runs/<ts>-maze/nostim.json --nostim
"""

import json
import os
import sys
import time
import urllib.request

BASE_URL = "http://127.0.0.1:8080"
JUNCTIONS = 10
LOOM_LEVEL = 0.8
STIM_MS = 400
SETTLE_MS = 1000        # settle before first junction
REFRACTORY_MS = 600     # settle after each decision
SEEDS = [12345, 12346, 12347]
# Pre-declared target path; the loom is applied on the OPPOSITE side each time.
TARGET_PATH = "RLRRLLRLLR"


def api(method, path, payload=None):
    data = json.dumps(payload or {}).encode()
    req = urllib.request.Request(
        BASE_URL + path, data=data if method == "POST" else None, method=method,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def junction(seed, loom_side, nostim=False):
    """One junction: loom the wrong side, count lateralized command spikes."""
    api("POST", "/set_input",
        {"loomL": 0.0 if (nostim or loom_side == "R") else LOOM_LEVEL,
         "loomR": 0.0 if (nostim or loom_side == "L") else LOOM_LEVEL})
    dL = dR = gf = escw = 0
    for _ in range(STIM_MS):
        api("POST", "/step", {"ms": 1})
        ls = api("GET", "/read")["last_step"]
        dL += ls["dnaL"]; dR += ls["dnaR"]; gf += ls["gf"]; escw += ls["escw"]
    api("POST", "/set_input", {"loomL": 0.0, "loomR": 0.0})
    # Decision: dominant dna side = turn direction (loomL -> dnaR -> turn R,
    # i.e. away from the looming wall). Correct turn = opposite the loom.
    if dL == dR:
        choice = "TIE"
    else:
        choice = "L" if dL > dR else "R"
    correct = (loom_side == "N/A") or (choice != loom_side)
    return {"loom_side": loom_side, "dnaL": dL, "dnaR": dR, "gf": gf,
            "escw": escw, "choice": choice, "correct": correct}


def run_maze(seed, nostim=False):
    api("POST", "/reset", {"seed": seed})
    api("POST", "/step", {"ms": SETTLE_MS})
    junctions = []
    for k in range(JUNCTIONS):
        wrong = "L" if TARGET_PATH[k] == "R" else "R"
        js = junction(seed, "N/A" if nostim else wrong, nostim=nostim)
        js["junction"] = k
        junctions.append(js)
        api("POST", "/step", {"ms": REFRACTORY_MS})
    if nostim:
        score = None  # no correct answer exists without stimuli
    else:
        score = sum(j["correct"] for j in junctions)
    return {"seed": seed, "nostim": nostim, "score": score,
            "of": JUNCTIONS, "junctions": junctions}


def main():
    global BASE_URL
    args = sys.argv[1:]
    port = 8080
    label = "intact"
    nostim = False
    outfile = None
    if "--port" in args:
        port = int(args[args.index("--port") + 1]); BASE_URL = f"http://127.0.0.1:{port}"
    if "--label" in args:
        label = args[args.index("--label") + 1]
    if "--nostim" in args:
        nostim = True; label = "nostim_control"
    if "--out" in args:
        outfile = os.path.expanduser(args[args.index("--out") + 1])

    hello = api("GET", "/status")
    shuffled = hello.get("shuffled", False)
    print(f"kernel: n={hello['n']} e={hello['e']} device={hello['device']} "
          f"shuffled={shuffled} shuffle_seed={hello.get('shuffle_seed')}")

    runs = []
    t0 = time.time()
    for seed in SEEDS:
        r = run_maze(seed, nostim=nostim)
        runs.append(r)
        sc = "n/a" if r["score"] is None else f"{r['score']}/{r['of']}"
        choices = "".join(j["choice"][0] if j["choice"] != "TIE" else "-" for j in r["junctions"])
        print(f"seed={seed} [{label}] score={sc} choices={choices}")

    result = {
        "experiment": "maze_navigation_threat_avoidance",
        "phase": "V",
        "kernel_version": hello.get("version"),
        "device": hello.get("device"),
        "connectome": {"n": hello["n"], "e": hello["e"]},
        "arm": "shuffled_control" if shuffled else "intact_connectome",
        "label": label,
        "shuffle_seed": hello.get("shuffle_seed"),
        "target_path": TARGET_PATH,
        "params": {"junctions": JUNCTIONS, "loom_level": LOOM_LEVEL,
                   "stim_ms": STIM_MS, "settle_ms": SETTLE_MS,
                   "refractory_ms": REFRACTORY_MS},
        "decision_rule": "dnaL vs dnaR spike counts over stimulus window; "
                         "dominant side = turn; correct = opposite loom; "
                         "ties = no-decision",
        "stimulus_port": "loomL/loomR via set_input (real sensory drive path)",
        "seeds": SEEDS,
        "wall_seconds": round(time.time() - t0, 2),
        "timestamp": time.time(),
        "runs": runs,
    }
    if outfile:
        os.makedirs(os.path.dirname(outfile), exist_ok=True)
        with open(outfile, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nSaved {len(runs)} maze runs -> {outfile}")


if __name__ == "__main__":
    main()
