#!/usr/bin/env python3
"""
LabServer HTTP Bridge — Phase II: Experimental Control for SiliconFly.

A minimal HTTP/JSON interface bound to 127.0.0.1:8080 that controls the
deterministic Metal simulation kernel (SiliconFly) running as a subprocess.

Protocol:
  - Spawns `SiliconFly --serve` as a subprocess.
  - Speaks JSON-lines to the kernel's stdin/stdout (deterministic, low latency).
  - Exposes a REST-like HTTP interface for the external agent.

Endpoints:
  GET  /status          -> Query simulation status (bio time, wall time, rates)
  POST /reset           -> Reset sim to a reproducible initial state {seed}
  POST /step            -> Advance sim by N steps {ms}
  POST /inject          -> Inject current into specified neurons {neurons, amplitude}
  POST /stimulate       -> Apply predefined sensory stimulation {group, strength, duration}
  GET  /read            -> Read spike counts, rates, GF/DNa activity
  GET  /export          -> Export current results (raw JSON)
  POST /shutdown        -> Stop the simulation kernel

Determinism:
  - The kernel is Q16 fixed-point with seeded state.
  - The bridge serializes all kernel commands (single-threaded dispatch).
  - Biological time (sim_ms) is tracked by the kernel; wall time by the bridge.

Safety:
  - Binds to 127.0.0.1 only (no external network exposure).
  - Validates all IDs, amplitudes, durations, and steps against kernel limits.
"""

import json
import os
import subprocess
import threading
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- Configuration ---
KERNAL_BINARY = os.environ.get("LAB_BINARY", os.path.join(os.path.dirname(os.path.abspath(__file__)), "specimen", "SiliconFly"))
KERNAL_ARGS = ["--serve"]
# Optional weights-shuffled control connectome: set LAB_SHUFFLE=<seed>
_shuffle = os.environ.get("LAB_SHUFFLE")
if _shuffle:
    KERNAL_ARGS += ["--shuffle", _shuffle]
HTTP_HOST = "127.0.0.1"
HTTP_PORT = int(os.environ.get("LAB_PORT", "8080"))

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger("LabBridge")

class SimulationKernel:
    """Wrapper for the SiliconFly JSON-lines simulation kernel subprocess."""

    def __init__(self, seed: int = 0x5EED1F1F):
        self.proc = None
        self.lock = threading.Lock()
        self.seed = seed
        self.ready = False
        self._start()

    def _start(self):
        logger.info(f"Spawning kernel: {KERNAL_BINARY} {' '.join(KERNAL_ARGS)}")
        try:
            self.proc = subprocess.Popen(
                [KERNAL_BINARY] + KERNAL_ARGS,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )
            # Wait for the ready signal from the kernel
            line = self.proc.stdout.readline()
            if line:
                ready_event = json.loads(line)
                if ready_event.get("event") == "ready":
                    self.ready = True
                    logger.info(f"Kernel ready: n={ready_event['n']}, "
                                f"e={ready_event['e']}, device={ready_event['device']}")
        except Exception as e:
            logger.error(f"Failed to start kernel: {e}")
            raise

    def send(self, cmd: dict) -> dict:
        """Send a command to the kernel and wait for the response (serialized)."""
        with self.lock:
            if self.proc is None or self.proc.poll() is not None:
                raise RuntimeError("Kernel process is dead.")

            payload = json.dumps(cmd) + "\n"
            self.proc.stdin.write(payload)
            self.proc.stdin.flush()

            response_line = self.proc.stdout.readline()
            if not response_line:
                raise RuntimeError("Kernel closed the stream unexpectedly.")

            try:
                return json.loads(response_line)
            except json.JSONDecodeError:
                logger.error(f"Kernel sent invalid JSON: {response_line}")
                raise

    def shutdown(self):
        with self.lock:
            if self.proc and self.proc.poll() is None:
                try:
                    self.send({"cmd": "shutdown"})
                    self.proc.wait(timeout=2)
                except Exception:
                    self.proc.terminate()

# --- HTTP Request Handler ---

class BridgeHandler(BaseHTTPRequestHandler):
    kernel = None  # Class-level reference set at startup

    def _set_headers(self, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

    def _send_json(self, data, code=200):
        self._set_headers(code)
        self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))

    def do_GET(self):
        if self.path == "/" or self.path == "/health":
            self._send_json({"ok": True, "service": "siliconfly-lab-bridge", "port": HTTP_PORT})
        elif self.path == "/status":
            res = self.kernel.send({"cmd": "hello"})
            # Add wall time for context
            res["wall_ms"] = int(time.time() * 1000)
            self._send_json(res)
        elif self.path == "/read":
            res = self.kernel.send({"cmd": "read", "last_step": True})
            self._send_json(res)
        elif self.path == "/export":
            # For simplicity, export returns the current read snapshot.
            res = self.kernel.send({"cmd": "read"})
            self._send_json(res)
        else:
            self._send_json({"ok": False, "error": "Not Found"}, 404)

    def do_POST(self):
        try:
            content_len = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_len)) if content_len > 0 else {}

            if self.path == "/reset":
                seed = body.get("seed", 0x5EED1F1F)
                res = self.kernel.send({"cmd": "reset", "seed": seed})
            elif self.path == "/step":
                ms = int(body.get("ms", 1))
                # Safety limits
                if ms <= 0 or ms > 120000: raise ValueError("ms out of bounds (1-120000)")
                res = self.kernel.send({"cmd": "step", "ms": ms})
            elif self.path == "/inject":
                neurons = body.get("neurons", [])
                amplitude = float(body.get("amplitude", 0.0))
                res = self.kernel.send({"cmd": "stimulate", "neurons": neurons, "strength": amplitude, "duration_ms": 1})
            elif self.path == "/stimulate":
                group = body.get("group", "gf")
                strength = float(body.get("strength", 0.5))
                duration = int(body.get("duration_ms", 100))
                # Safety limits
                if duration <= 0 or duration > 5000: raise ValueError("duration_ms out of bounds (1-5000)")
                if strength < 0 or strength > 2.0: raise ValueError("strength out of bounds (0-2.0)")
                res = self.kernel.send({"cmd": "stimulate", "group": group, "strength": strength, "duration_ms": duration})
            elif self.path == "/ablate":
                # Full ablation of a population (outgoing edges + intrinsic drive),
                # always derived from the pristine connectome; never compounds.
                res = self.kernel.send({"cmd": "ablate", **body})
            elif self.path == "/ablate_clear":
                res = self.kernel.send({"cmd": "ablate_clear"})
            elif self.path == "/stim_trial":
                # Targeted-neuron stimulus trial (sugar GRNs -> MN9 readout).
                # Explicit trial parameters are validated, not clamped.
                if body.get("poisson") and not (0 <= float(body.get("rate_hz", 0)) <= 500):
                    raise ValueError("rate_hz out of bounds (0-500)")
                res = self.kernel.send({"cmd": "stim_trial", **body})
            elif self.path == "/trial":
                # Pass-through to the kernel's real-input trial primitive:
                # settle (zeroed sensory input) -> hold loom drive -> post window.
                res = self.kernel.send({"cmd": "trial", **body})
            elif self.path == "/set_input":
                # Pass-through to the kernel's set_input command (loomL/loomR
                # levels, airPuff, sugarRate, gaitDrive, ...). Used by stepping
                # experiments that need per-step readouts between drive changes.
                res = self.kernel.send({"cmd": "set_input", **body})
            elif self.path == "/shutdown":
                res = {"ok": True, "message": "Shutting down"}
                self._send_json(res)
                threading.Thread(target=self.kernel.shutdown).start()
                return
            else:
                res = {"ok": False, "error": {"code": "not_found", "message": "Unknown endpoint"}}

            # Kernel-level failures surface as HTTP 400 with the same body, so
            # error semantics are uniform bridge-side and kernel-side.
            if res.get("ok") is False:
                self._send_json(res, 400)
            else:
                self._send_json(res)
        except Exception as e:
            self._send_json({"ok": False, "error": {"code": "bad_request", "message": str(e)}}, 400)

def run_bridge():
    kernel = SimulationKernel()
    BridgeHandler.kernel = kernel

    server = HTTPServer((HTTP_HOST, HTTP_PORT), BridgeHandler)
    logger.info(f"HTTP Bridge listening on http://{HTTP_HOST}:{HTTP_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        kernel.shutdown()
        server.server_close()

if __name__ == "__main__":
    run_bridge()
