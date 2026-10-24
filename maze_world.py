#!/usr/bin/env python3
"""
maze_world.py — deterministic 2D maze world + point agent for Buzz.

Engineered approximations, documented explicitly:
- Buzz is a point agent: position (x, y), heading (rad, 0 = +x, CCW positive),
  fixed forward speed, angular velocity from the neural decoder.
- Walls are axis-aligned segments on a unit grid. Collision = circle-vs-segment;
  on collision the agent is projected out along the wall normal (slide), the
  collision is counted, and the episode continues.
- Sensory encoding: three whisker ray-casts (left -35 deg, forward, right +35
  deg). Wall proximity p = clamp(1 - d / WHISKER_MAX, 0, 1) per ray.
  loomL = max(left ray, forward ray), loomR = max(right ray, forward ray).
  This maps obstacle proximity into the existing scalar looming channels.
  It is NOT biologically realistic vision (no looming expansion dynamics);
  the mapping is fixed and identical across all conditions.

The maze geometry (walls, start, exit) is never supplied to the neural side:
the brain sees only the two scalar loom levels and returns only spike activity.
"""

import math

WHISKER_FAN_DEG = (-75.0, -45.0, -20.0, 0.0, 20.0, 45.0, 75.0)
WHISKER_MAX = 1.2          # ray length, world units
APPROACH_GAIN = 60.0       # loom level per unit per-tick proximity increase
AGENT_RADIUS = 0.12
FORWARD_SPEED = 0.001      # world units per sim ms (1 unit per sim second)
MAX_OMEGA = 0.003          # rad per sim ms (3 rad per sim second), bounded gain


def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


class Maze:
    """Walls as axis-aligned segments: (x1, y1, x2, y2). Plus start/exit."""

    def __init__(self, walls, start, start_heading, exit_pt, name, mirror=False):
        self.name = name + ("_mirror" if mirror else "")
        self.mirror = mirror
        if mirror:
            xs = [w[0] for w in walls] + [w[2] for w in walls]
            width = max(xs)
            walls = [(width - w[2], w[1], width - w[0], w[3]) for w in walls]
            start = (width - start[0], start[1])
            start_heading = math.pi - start_heading
            exit_pt = (width - exit_pt[0], exit_pt[1])
        self.walls = walls
        self.start = start
        self.start_heading = start_heading
        self.exit = exit_pt

    def raycast(self, x, y, ang, max_d=WHISKER_MAX):
        """Distance to nearest wall along ray, or max_d."""
        dx, dy = math.cos(ang), math.sin(ang)
        best = max_d
        for (x1, y1, x2, y2) in self.walls:
            ex, ey = x2 - x1, y2 - y1
            den = dx * ey - dy * ex
            if abs(den) < 1e-12:
                continue
            t = ((x1 - x) * ey - (y1 - y) * ex) / den       # along ray
            u = ((x1 - x) * dy - (y1 - y) * dx) / den       # along wall
            if t > 1e-9 and 0.0 <= u <= 1.0 and t < best:
                best = t
        return best


def corridor_one_turn(mirror=False):
    """L1: east corridor (y 0..1), single left turn, north to exit (9.5, 9.5)."""
    walls = [
        (0, 0, 10, 0),        # south
        (10, 0, 10, 10),      # east outer
        (0, 0, 0, 1),         # west cap
        (0, 1, 9, 1),         # inner horizontal (gap x 9..10)
        (9, 1, 9, 10),        # inner vertical
        (9, 10, 10, 10),      # north cap
    ]
    return Maze(walls, (0.5, 0.5), 0.0, (9.5, 9.5), "corridor1", mirror)


def corridor_two_turns(mirror=False):
    """L2: S-shaped: east, north, west, north to exit (0.5, 9.5)."""
    walls = [
        (0, 0, 10, 0),        # south
        (10, 0, 10, 10),      # east outer
        (0, 0, 0, 10),        # west outer
        (1, 10, 10, 10),      # north (gap x 0..1)
        (0, 10, 1, 10),       # north cap over left corridor
        (0, 1, 9, 1),         # bottom corridor ceiling (gap x 9..10)
        (9, 1, 9, 5),         # right corridor inner wall (gap y 5..6)
        (0, 5, 9, 5),         # middle corridor floor
        (1, 6, 10, 6),        # middle corridor ceiling (gap x 0..1)
        (1, 6, 1, 10),        # left corridor inner wall
    ]
    return Maze(walls, (0.5, 0.5), 0.0, (0.5, 9.5), "corridor2", mirror)


class Agent:
    def __init__(self, maze):
        self.maze = maze
        self.x, self.y = maze.start
        self.heading = maze.start_heading
        self.omega = 0.0           # actual angular velocity (actuator lag)
        self.prev_prox = None      # for approach-rate sensory encoding
        self.collisions = 0
        self.trajectory = [(self.x, self.y)]
        self.path_len = 0.0

    def sense(self):
        """Approach-rate (looming) encoding.

        Looming detectors respond to EXPANDING edges, not static proximity:
        a wall held at constant distance is not a looming threat (the phasic
        silence of the command neurons under sustained drive, observed in
        closed-loop smoke tests, matches this). So each side's loom level is
        the per-tick INCREASE in wall proximity on that side (rectified
        closing rate), scaled to 0..1. The forward ray feeds both channels.
        Consistent across all conditions. NOT biologically realistic vision:
        scalar channels, no angular expansion geometry.
        """
        m = self.maze
        def prox(d):
            return (1.0 - clamp(d / WHISKER_MAX, 0.0, 1.0)) ** 2
        pL = pR = pF = 0.0
        dL_min = dR_min = WHISKER_MAX
        distF = WHISKER_MAX
        for deg in WHISKER_FAN_DEG:
            d = m.raycast(self.x, self.y, self.heading + math.radians(deg))
            p = prox(d)
            if deg > 0:          # left side
                pL = max(pL, p); dL_min = min(dL_min, d)
            elif deg < 0:        # right side
                pR = max(pR, p); dR_min = min(dR_min, d)
            else:                # forward ray feeds BOTH channels
                pF = p; distF = d
        if self.prev_prox is None:
            self.prev_prox = (pL, pR, pF)
            riseL = riseR = 0.0
        else:
            qL, qR, qF = self.prev_prox
            riseL = max(0.0, max(pL, pF) - max(qL, qF))
            riseR = max(0.0, max(pR, pF) - max(qR, qF))
            self.prev_prox = (pL, pR, pF)
        return {"loomL": clamp(APPROACH_GAIN * riseL, 0.0, 1.0),
                "loomR": clamp(APPROACH_GAIN * riseR, 0.0, 1.0),
                "proxL": pL, "proxR": pR, "proxF": pF,
                "distL": dL_min, "distF": distF, "distR": dR_min}

    def move(self, omega_cmd, dt=1.0, actuator_alpha=0.2):
        """One sim step: first-order angular actuator (tau ~= 40 ms at 100 Hz
        control), rotate, advance, resolve collision (slide along wall)."""
        self.omega += (omega_cmd - self.omega) * actuator_alpha
        self.heading += self.omega * dt
        nx = self.x + FORWARD_SPEED * math.cos(self.heading) * dt
        ny = self.y + FORWARD_SPEED * math.sin(self.heading) * dt
        collided = False
        for (x1, y1, x2, y2) in self.maze.walls:
            ex, ey = x2 - x1, y2 - y1
            L2 = ex * ex + ey * ey
            t = clamp(((nx - x1) * ex + (ny - y1) * ey) / L2, 0.0, 1.0)
            cx, cy = x1 + t * ex, y1 + t * ey
            ddx, ddy = nx - cx, ny - cy
            d2 = ddx * ddx + ddy * ddy
            if d2 < AGENT_RADIUS * AGENT_RADIUS:
                collided = True
                d = math.sqrt(d2) or 1e-9
                nxn, nyn = ddx / d, ddy / d          # wall->agent normal
                nx = cx + nxn * AGENT_RADIUS
                ny = cy + nyn * AGENT_RADIUS
                # specular reflection of the heading about the wall plane
                vx, vy = math.cos(self.heading), math.sin(self.heading)
                dot = vx * nxn + vy * nyn
                if dot < 0:                           # moving into the wall
                    rx, ry = vx - 2 * dot * nxn, vy - 2 * dot * nyn
                    self.heading = math.atan2(ry, rx)
        self.path_len += math.hypot(nx - self.x, ny - self.y)
        self.x, self.y = nx, ny
        if collided:
            self.collisions += 1
        self.trajectory.append((self.x, self.y))
        return collided

    def at_exit(self, tol=0.55):
        return math.hypot(self.x - self.maze.exit[0],
                          self.y - self.maze.exit[1]) <= tol
