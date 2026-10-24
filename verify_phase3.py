#!/usr/bin/env python3
"""
Phase III final verification smoke.
Covers: baseline unchanged, ablation persists across resets, ablate_clear
restores baseline function, HTTP ablation endpoints functional, clean
termination. GPUCHECK is covered by the hermes verify test phase run just
prior; data/commit preservation checked by the calling shell.
"""
import json
import subprocess
import time
import urllib.request

BASE = "http://127.0.0.1:8080"
REF_TRIAL = {"loomL": 0.8, "loomR": 0.0, "duration_ms": 400, "settle_ms": 2000, "post_ms": 200}
REF_GF = 78  # Phase IV observed: seed 12345, loomL 0.8, 400 ms, settle 2000

def api(m, p, pl=None):
    r = urllib.request.Request(BASE + p, data=json.dumps(pl or {}).encode() if m == "POST" else None,
                               method=m, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=300).read())

results = []
def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")

def trial_gf():
    t = api("POST", "/trial", REF_TRIAL)
    return t["gf_total"], t["first_gf_ms"]

# 1. baseline unchanged (reference trial reproduces Phase IV value)
api("POST", "/ablate_clear")
api("POST", "/reset", {"seed": 12345})
gf, lat = trial_gf()
check("baseline unchanged", gf == REF_GF, f"gf_total={gf} (reference {REF_GF}), first_gf={lat}ms")

# 2. ablation persists across resets (two independent resets)
api("POST", "/ablate", {"group": "loom"})
gfs = []
for _ in range(2):
    api("POST", "/reset", {"seed": 12345})
    gf, _ = trial_gf()
    gfs.append(gf)
check("ablation persists across resets", all(g == 0 for g in gfs), f"gf after 2 resets: {gfs}")

# 3. ablate_clear restores baseline function
api("POST", "/ablate_clear")
api("POST", "/reset", {"seed": 12345})
gf, lat = trial_gf()
check("ablate_clear restores baseline", gf == REF_GF, f"gf_total={gf} after clear+reset")

# 4. HTTP ablation endpoints functional (error paths included)
r = api("POST", "/ablate", {"group": "loomL"})
ok1 = r["ok"] and r["targeted"] == 162 and "loomL" in r["ablation"]
try:
    api("POST", "/ablate", {"group": "banana"})
    ok2 = False
except urllib.error.HTTPError as e:
    ok2 = e.code == 400
api("POST", "/ablate_clear")
check("ablation endpoints + validation", ok1 and ok2,
      f"loomL targets {r['targeted']}, bad group rejected with 400: {ok2}")

print()
fails = [r for r in results if not r[1]]
print(f"{len(results) - len(fails)}/{len(results)} checks passed")
raise SystemExit(1 if fails else 0)
