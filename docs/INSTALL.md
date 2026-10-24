# Installation and reproduction

macOS with a Metal GPU and full Xcode required. Nothing is installed system-wide, and no
services persist.

## 1. Clone with the kernel submodule

```sh
git clone --recurse-submodules https://github.com/archpc/buzz-flywire-lab
cd buzz-flywire-lab
```

`specimen/` is [archpc/siliconfly@lab-bridge](https://github.com/archpc/siliconfly/tree/lab-bridge):
upstream SiliconFly `8839d84` plus 7 lab commits. The FlyWire v783 connectome (~95 MB,
CC BY-NC 4.0) ships in `specimen/data/`.

## 2. Build and validate the kernel

```sh
cd specimen
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer   # if xcode-select points at CommandLineTools
./build.sh
./SiliconFly --gpucheck   # GPU/CPU bit-exactness + determinism (~10 s) -> GPUCHECK PASS
./SiliconFly --simtest    # circuit diagnostics (~40 s) -> PASS
cd ..
```

## 3. Bridge (stdlib Python, binds 127.0.0.1 only)

```sh
python3 buzz.py start                                # intact connectome on :8080
python3 buzz.py --port 8081 start --shuffle 12648430 # shuffled control (12648430 = 0xC0FFEE; --port goes BEFORE the subcommand; --shuffle is decimal)
python3 buzz.py call GET /status
python3 buzz.py stop                                 # expect "lingering_pids": []
```

Or run the bridge directly: `LAB_PORT=8080 python3 lab.py`. Use `LAB_SHUFFLE=0xC0FFEE` (the
kernel accepts hex here) for the control, and `LAB_BINARY` to override the kernel path.

## 4. Determinism spot-check against a published trial

```sh
python3 buzz.py start
python3 buzz.py call POST /reset '{"seed": 12345}'
python3 buzz.py call POST /stim_trial '{"neurons": [69416,98045,123346,124845,29414,101067,110984,51345,49815,130314,127443,28958,127169,127322,33003,108934,111872,14903,91001,92717,12549], "watch": [138947], "strength": 0.5, "duration_ms": 1000, "settle_ms": 2000, "post_ms": 200}'
# expect watch_totals[0] == 82 (MN9) and gf_total == 0, matching data/banana_peel.json
python3 buzz.py stop
```

## 5. Analysis

```sh
uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r requirements.txt
for a in escape ablation mirror banana; do .venv/bin/python analyze_$a.py; done   # -> figs/
```

## 6. Running experiments

Accepted datasets in `data/*.json` are immutable. Several `run_*.py` scripts write into
`data/` by default. Use `--out data/runs/<UTC-timestamp>-<slug>/...` where supported
(`run_experiment.py`, `run_maze.py`, `run_closed_loop.py`). Otherwise work in a copy, so you
don't overwrite published records.
