#!/usr/bin/env python3
"""
neural_bridge.py — thin client for the SiliconFly lab bridge (127.0.0.1 only).

Closed-loop contract used by the maze runner:
  reset(seed) -> settle via step() -> per control tick:
    set_input(loomL, loomR)  # scalar sensory channels (engineered proximity map)
    step(TICK_MS)            # advance the brain
    read_rates()             # dnaL/dnaR EMA population rates (Hz)
Sign convention (verified 2026-10-19, per-step probe, seed 12345):
  loomL -> dnaR dominates (48 vs 4 spikes)  => turn RIGHT (away)
  loomR -> dnaL dominates (41 vs 19 spikes) => turn LEFT  (away)
  decoder: omega = +K * (dnaL_rate - dnaR_rate); positive omega = CCW (left).
"""

import json
import urllib.request


class Bridge:
    def __init__(self, port):
        self.base = f"http://127.0.0.1:{port}"

    def _call(self, method, path, payload=None):
        data = json.dumps(payload or {}).encode()
        req = urllib.request.Request(
            self.base + path, data=data if method == "POST" else None,
            method=method, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            res = json.loads(r.read())
        if res.get("ok") is False:
            raise RuntimeError(f"bridge error {path}: {res.get('error')}")
        return res

    def status(self):
        return self._call("GET", "/status")

    def reset(self, seed):
        return self._call("POST", "/reset", {"seed": seed})

    def step(self, ms):
        return self._call("POST", "/step", {"ms": ms})

    def set_input(self, loomL=0.0, loomR=0.0):
        return self._call("POST", "/set_input", {"loomL": loomL, "loomR": loomR})

    def read(self):
        return self._call("GET", "/read")

    def rates(self):
        return self._call("GET", "/read")["rates"]

    def step_accumulate(self, ms):
        """Step `ms` sim-ms one ms at a time, accumulating per-step last_step
        group counts. Unlagged readout: per-step spike counts, no EMA
        smoothing. Returns dict with per-tick totals."""
        c = {"dnaL": 0, "dnaR": 0, "gf": 0, "escw": 0, "fwd": 0}
        for _ in range(ms):
            self._call("POST", "/step", {"ms": 1})
            ls = self._call("GET", "/read")["last_step"]
            for k in c:
                c[k] += ls[k]
        return c

    def ablate(self, group):
        return self._call("POST", "/ablate", {"group": group})

    def ablate_clear(self):
        return self._call("POST", "/ablate_clear")
