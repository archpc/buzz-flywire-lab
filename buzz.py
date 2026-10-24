#!/usr/bin/env python3
"""
buzz — lifecycle manager for the Drosophila lab (SiliconFly kernel + lab.py bridge).

Single entry point so an agent never has to babysit processes:
  buzz status                        # bridge/kernel state, kernel identity JSON
  buzz start [--port N] [--shuffle SEED] [--timeout S]
                                     # reuse healthy instance; spawn if down
  buzz call METHOD PATH [JSON] [--timeout S]
                                     # thin passthrough to the bridge API
  buzz stop                          # POST /shutdown, verify port closed, pkill fallback

stdlib only. Binds stay on 127.0.0.1 (enforced by lab.py, never changed here).
On-demand by design: no daemon, no LaunchAgent. Stop the fly when done.
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

HOME = os.environ.get("BUZZ_HOME", os.path.dirname(os.path.abspath(__file__)))
LAB = os.path.join(HOME, "lab.py")
LOGDIR = os.path.join(HOME, "logs")


def _ere(text):
    """Escape a literal path for pgrep/pkill extended regex."""
    return "".join("\\" + c if c in ".[]()*+?^${}|\\" else c for c in text)


# Process-sweep patterns derive from this checkout's location, so stop/evict
# work wherever the lab lives (previously hardcoded to a 'drosophila/' path,
# which silently matched nothing in other checkouts).
LAB_PAT = _ere(LAB)
KERNEL_PAT = _ere(os.path.join(HOME, "specimen", "SiliconFly")) + " --serve"
DEFAULT_PORT = 8080


def base_url(port):
    return f"http://127.0.0.1:{port}"


def http(method, url, body=None, timeout=10):
    data = None
    req = urllib.request.Request(url, method=method)
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, data=data, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw) if raw.strip() else {}


def healthy(port):
    # /status, not /: a bridge whose kernel died still serves / but is unusable.
    try:
        http("GET", base_url(port) + "/status", timeout=5)
        return True
    except Exception:
        return False


def port_in_use(port):
    import socket
    with socket.socket() as s:
        s.settimeout(2)
        return s.connect_ex(("127.0.0.1", port)) == 0


def get_status(port):
    try:
        return http("GET", base_url(port) + "/status", timeout=10)
    except Exception as e:
        return {"ok": False, "error": f"status failed: {type(e).__name__}: {e}"}


def cmd_status(args):
    if not healthy(args.port):
        print(json.dumps({"running": False, "port": args.port}))
        return 0
    print(json.dumps({"running": True, "port": args.port, **get_status(args.port)}))
    return 0


def cmd_start(args):
    if healthy(args.port):
        st = get_status(args.port)
        shuffled = st.get("shuffled", False)
        want_shuffle = args.shuffle is not None
        if want_shuffle != bool(shuffled):
            print(json.dumps({
                "error": "port occupied by a different arm",
                "running_shuffle": shuffled,
                "requested_shuffle": args.shuffle,
                "hint": f"buzz stop --port {args.port} first, or use another --port",
            }))
            return 2
        if want_shuffle and int(st.get("shuffle_seed", -1)) != int(args.shuffle):
            print(json.dumps({
                "error": "port occupied by a different shuffle seed",
                "running_shuffle_seed": st.get("shuffle_seed"),
                "requested_shuffle_seed": args.shuffle,
                "hint": f"buzz stop --port {args.port} first, or use another --port",
            }))
            return 2
        print(json.dumps({"reused": True, "port": args.port, **st}))
        return 0

    if port_in_use(args.port):
        # Broken bridge/kernel occupies the port (health check already failed):
        # evict it, then respawn fresh.
        subprocess.run(["pkill", "-f", LAB_PAT], capture_output=True)
        subprocess.run(["pkill", "-f", KERNEL_PAT],
                       capture_output=True)
        deadline = time.time() + 10
        while time.time() < deadline and port_in_use(args.port):
            time.sleep(0.5)
        if port_in_use(args.port):
            print(json.dumps({"error": "port occupied, eviction failed",
                              "port": args.port}))
            return 1

    os.makedirs(LOGDIR, exist_ok=True)
    log_path = os.path.join(LOGDIR, f"bridge-{args.port}.log")
    env = dict(os.environ)
    env["LAB_PORT"] = str(args.port)
    if args.shuffle is not None:
        env["LAB_SHUFFLE"] = str(args.shuffle)
    with open(log_path, "ab") as logf:
        subprocess.Popen(
            [sys.executable, LAB],
            cwd=HOME, env=env, stdout=logf, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    deadline = time.time() + args.timeout
    last = None
    while time.time() < deadline:
        if healthy(args.port):
            print(json.dumps({"started": True, "reused": False, "port": args.port,
                              "log": log_path, **get_status(args.port)}))
            return 0
        time.sleep(0.5)
        try:
            last = open(log_path, "rb").read()[-400:].decode(errors="replace")
        except OSError:
            last = None
    print(json.dumps({"error": "bridge did not become healthy", "port": args.port,
                      "log": log_path, "log_tail": last}))
    return 1


def proc_linger():
    r = subprocess.run(["pgrep", "-f", LAB_PAT + "|" + KERNEL_PAT],
                       capture_output=True, text=True)
    return [int(x) for x in r.stdout.split()]


def cmd_stop(args):
    # Politely ask the bridge to shut itself (and the kernel) down.
    if healthy(args.port):
        try:
            http("POST", base_url(args.port) + "/shutdown", timeout=15)
        except (urllib.error.URLError, OSError):
            pass  # bridge may drop the connection mid-shutdown; verify below
    deadline = time.time() + 10
    while time.time() < deadline and (healthy(args.port) or port_in_use(args.port)):
        time.sleep(0.5)
    # The bridge can close its listener yet hang without reaping the kernel
    # child (observed: port closed, lab.py + SiliconFly --serve alive at 0% CPU).
    # Sweep scoped patterns and verify by process list, not port state.
    if proc_linger():
        subprocess.run(["pkill", "-f", LAB_PAT], capture_output=True)
        subprocess.run(["pkill", "-f", KERNEL_PAT],
                       capture_output=True)
        deadline = time.time() + 5
        while time.time() < deadline and proc_linger():
            time.sleep(0.5)
    left = proc_linger()
    if left:  # last resort: SIGKILL
        for pid in left:
            subprocess.run(["kill", "-9", str(pid)], capture_output=True)
        time.sleep(1)
        left = proc_linger()
    down = (not healthy(args.port)) and not left
    print(json.dumps({"stopped": down, "port": args.port,
                      "port_closed": not port_in_use(args.port),
                      "lingering_pids": left}))
    return 0 if down else 1


def cmd_call(args):
    url = base_url(args.port) + args.path
    body = json.loads(args.json) if args.json else None
    try:
        out = http(args.method.upper(), url, body=body, timeout=args.timeout)
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            out = json.loads(raw)
        except ValueError:
            out = {"error": raw}
        print(json.dumps(out))
        return 1
    except urllib.error.URLError as e:
        print(json.dumps({"ok": False, "error": f"bridge unreachable: {e.reason}",
                          "hint": "buzz start"}))
        return 1
    print(json.dumps(out))
    return 0


def main():
    p = argparse.ArgumentParser(prog="buzz", description=__doc__)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")
    sp = sub.add_parser("start")
    sp.add_argument("--shuffle", type=int, default=None)
    sp.add_argument("--timeout", type=int, default=60)
    cp = sub.add_parser("call")
    cp.add_argument("method")
    cp.add_argument("path")
    cp.add_argument("json", nargs="?", default=None)
    cp.add_argument("--timeout", type=int, default=300)
    sub.add_parser("stop")

    args = p.parse_args()
    return {"status": cmd_status, "start": cmd_start,
            "call": cmd_call, "stop": cmd_stop}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
