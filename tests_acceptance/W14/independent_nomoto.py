#!/usr/bin/env python3
"""Independent W14 What-if check: Nomoto RK4 + OBB geometry.

Does not import or call the C# implementation. Compares verdict categories
and numerical deviations against the C# dump (logs/w14-scenario-dump.json)
and against the implementer's announced numbers.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Tuple

MPS_PER_KN = 1852.0 / 3600.0
METERS_PER_NM = 1852.0
SAFE_M = 0.1 * METERS_PER_NM

# Heading-hold PD, documented in NomotoSimulator.
KP = 1.2
KD = 10.0


def norm360(deg: float) -> float:
    m = deg % 360.0
    if m < 0:
        m += 360.0
    if m >= 360.0:
        m -= 360.0
    return m


def norm180(deg: float) -> float:
    m = deg % 360.0
    if m > 180.0:
        m -= 360.0
    if m < -180.0:
        m += 360.0
    return m


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


@dataclass
class Params:
    K: float
    T: float
    u_ref: float
    max_rudder: float = 35.0
    rudder_rate: float = 2.5
    speed_tau: float = 90.0
    stop_tau: float = 60.0
    astern_tau: float = 30.0
    min_speed: float = 0.0
    loa: float = 100.0
    beam: float = 16.0


@dataclass
class State:
    t: float
    east: float
    north: float
    psi: float  # unwrapped during integration
    r: float
    u: float
    rudder: float


@dataclass
class Intervention:
    kind: str  # turn, speed, stop, astern, hold, anchor
    t_exec: float
    rudder: float = 0.0
    heading_change: float = 0.0
    target_speed: float = 0.0
    anchor_side: str = "both"  # port/starboard/both
    bite_delay: float = 12.0
    anchor_decel: float = 0.08
    anchor_yaw: float = 0.30
    anchor_vmax: float = 6.0


def simulate(initial: State, p: Params, interventions: List[Intervention], end: float, dt: float = 0.1) -> List[State]:
    """Independent 1st-order Nomoto + 1st-order speed, RK4, rudder-rate limit, PD heading hold."""
    ordered = sorted(interventions, key=lambda x: x.t_exec)
    t = initial.t
    east, north = initial.east, initial.north
    psi, r, u = initial.psi, initial.r, max(initial.u, p.min_speed)
    rudder = clamp(initial.rudder, -p.max_rudder, p.max_rudder)
    speed_target = u
    speed_tau = p.speed_tau
    rudder_cmd = rudder
    turning = False
    turn_start = 0.0
    turn_change = 0.0
    holding = False
    hold_target = psi
    anchor_dropped = False
    anchor_eff = math.inf
    anchor_side = "both"
    anchor = None

    out = [State(t, east, north, psi, r, u, rudder)]
    if end <= t:
        return out

    ni = 0

    def derivatives(psi_, r_, u_, rudder_, anchor_decel, anchor_yaw):
        u_safe = max(u_, p.min_speed)
        dpsi = r_ + anchor_yaw
        dr = (p.K * (u_safe / p.u_ref) * rudder_ - r_) / p.T
        du = (speed_target - u_) / speed_tau - anchor_decel
        rad = psi_ * math.pi / 180.0
        speed_mps = u_safe * MPS_PER_KN
        de = speed_mps * math.sin(rad)
        dn = speed_mps * math.cos(rad)
        return dpsi, dr, du, de, dn

    while t < end - 1e-12:
        while ni < len(ordered) and ordered[ni].t_exec <= t + 1e-9:
            iv = ordered[ni]
            if iv.kind == "turn":
                rudder_cmd = clamp(iv.rudder, -p.max_rudder, p.max_rudder)
                if abs(iv.heading_change) > 1e-9:
                    turning = True
                    turn_start = psi
                    turn_change = iv.heading_change
                    holding = False
                else:
                    turning = False
                    holding = False
            elif iv.kind == "speed":
                speed_target = max(iv.target_speed, p.min_speed)
                speed_tau = p.speed_tau
            elif iv.kind == "stop":
                speed_target = p.min_speed
                speed_tau = p.stop_tau
            elif iv.kind == "astern":
                speed_target = p.min_speed
                speed_tau = p.astern_tau
            elif iv.kind == "hold":
                turning = False
                holding = True
                hold_target = psi
                speed_target = u
                speed_tau = p.speed_tau
            elif iv.kind == "anchor":
                anchor_dropped = True
                anchor_eff = iv.t_exec + iv.bite_delay
                anchor_side = iv.anchor_side
                anchor = iv
            ni += 1

        if turning:
            delta = psi - turn_start
            reached = (delta >= turn_change - 1e-6) if turn_change >= 0 else (delta <= turn_change + 1e-6)
            if reached:
                hold_target = turn_start + turn_change
                turning = False
                holding = True

        if holding:
            err = norm180(hold_target - psi)
            rudder_cmd = clamp(KP * err - KD * r, -p.max_rudder, p.max_rudder)

        step = min(dt, end - t)
        max_rd = p.rudder_rate * step
        rudder += clamp(rudder_cmd - rudder, -max_rd, max_rd)
        rudder = clamp(rudder, -p.max_rudder, p.max_rudder)

        a_decel = 0.0
        a_yaw = 0.0
        if anchor_dropped and t >= anchor_eff - 1e-9 and anchor is not None:
            red = anchor.anchor_vmax / u if u > anchor.anchor_vmax else 1.0
            a_decel = anchor.anchor_decel * red
            if anchor_side == "port":
                a_yaw = -anchor.anchor_yaw
            elif anchor_side == "starboard":
                a_yaw = anchor.anchor_yaw

        k1 = derivatives(psi, r, u, rudder, a_decel, a_yaw)
        k2 = derivatives(psi + k1[0] * step * 0.5, r + k1[1] * step * 0.5, u + k1[2] * step * 0.5, rudder, a_decel, a_yaw)
        k3 = derivatives(psi + k2[0] * step * 0.5, r + k2[1] * step * 0.5, u + k2[2] * step * 0.5, rudder, a_decel, a_yaw)
        k4 = derivatives(psi + k3[0] * step, r + k3[1] * step, u + k3[2] * step, rudder, a_decel, a_yaw)
        psi += step / 6.0 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        r += step / 6.0 * (k1[1] + 2 * k2[1] + 2 * k3[2 - 1] + k4[1])
        u += step / 6.0 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
        east += step / 6.0 * (k1[3] + 2 * k2[3] + 2 * k3[3] + k4[3])
        north += step / 6.0 * (k1[4] + 2 * k2[4] + 2 * k3[4] + k4[4])
        if u < p.min_speed:
            u = p.min_speed
        t += step
        out.append(State(t, east, north, psi, r, u, rudder))
    return out


def sample(states: List[State], t: float) -> State:
    if t <= states[0].t:
        s = states[0]
        return State(t, s.east, s.north, s.psi, s.r, s.u, s.rudder)
    if t >= states[-1].t:
        s = states[-1]
        return State(t, s.east, s.north, s.psi, s.r, s.u, s.rudder)
    lo, hi = 0, len(states) - 2
    while lo <= hi:
        mid = (lo + hi) // 2
        if t < states[mid].t:
            hi = mid - 1
        elif t > states[mid + 1].t:
            lo = mid + 1
        else:
            lo = mid
            break
    lo = max(0, min(len(states) - 2, lo))
    a, b = states[lo], states[lo + 1]
    span = b.t - a.t
    f = (t - a.t) / span if span > 1e-12 else 0.0
    dpsi = norm180(norm360(b.psi) - norm360(a.psi))
    return State(
        t,
        a.east + (b.east - a.east) * f,
        a.north + (b.north - a.north) * f,
        a.psi + dpsi * f,
        a.r + (b.r - a.r) * f,
        a.u + (b.u - a.u) * f,
        a.rudder + (b.rudder - a.rudder) * f,
    )


def corners(east, north, hdg, loa, beam):
    rad = norm360(hdg) * math.pi / 180.0
    s, c = math.sin(rad), math.cos(rad)
    fx, fy = s, c
    sx, sy = c, -s
    hl, hb = loa * 0.5, beam * 0.5
    return [
        (east + fx * hl + sx * hb, north + fy * hl + sy * hb),
        (east + fx * hl - sx * hb, north + fy * hl - sy * hb),
        (east - fx * hl - sx * hb, north - fy * hl - sy * hb),
        (east - fx * hl + sx * hb, north + fy * hl + sy * hb),  # wait: -fx*hl + sx*hb, -fy*hl + sy*hb
    ]


# Fix last corner typo - I'll fix after writing... actually I wrote a comment. Let me fix in a patch.
# The fourth corner should be: east - fx*hl + sx*hb, north - fy*hl + sy*hb

def sat_clearance(e1, n1, h1, l1, b1, e2, n2, h2, l2, b2) -> float:
    def axes(hdg):
        rad = norm360(hdg) * math.pi / 180.0
        s, c = math.sin(rad), math.cos(rad)
        return (s, c), (c, -s)

    af, asb = axes(h1)
    bf, bsb = axes(h2)
    d = (e2 - e1, n2 - n1)
    hl1, hb1, hl2, hb2 = l1 * 0.5, b1 * 0.5, l2 * 0.5, b2 * 0.5
    min_sep = math.inf
    min_pen = math.inf
    separated = False

    def dot(a, b):
        return a[0] * b[0] + a[1] * b[1]

    def norm(v):
        L = math.hypot(v[0], v[1])
        return (0.0, 0.0) if L < 1e-16 else (v[0] / L, v[1] / L)

    for axis in (af, asb, bf, bsb):
        axis = norm(axis)
        if axis[0] * axis[0] + axis[1] * axis[1] < 1e-16:
            continue
        proj = abs(dot(d, axis))
        ra = hl1 * abs(dot(af, axis)) + hb1 * abs(dot(asb, axis))
        rb = hl2 * abs(dot(bf, axis)) + hb2 * abs(dot(bsb, axis))
        gap = proj - (ra + rb)
        if gap > 0:
            separated = True
            min_sep = min(min_sep, gap)
        else:
            min_pen = min(min_pen, -gap)
    if separated:
        return 0.0 if min_sep == math.inf else min_sep
    return 0.0 if min_pen == math.inf else -min_pen


def point_seg_dist(p, a, b):
    abx, aby = b[0] - a[0], b[1] - a[1]
    len2 = abx * abx + aby * aby
    t = 0.0 if len2 <= 1e-18 else ((p[0] - a[0]) * abx + (p[1] - a[1]) * aby) / len2
    t = clamp(t, 0.0, 1.0)
    qx, qy = a[0] + t * abx, a[1] + t * aby
    return math.hypot(p[0] - qx, p[1] - qy), (qx, qy)


def true_distance(e1, n1, h1, l1, b1, e2, n2, h2, l2, b2) -> float:
    if sat_clearance(e1, n1, h1, l1, b1, e2, n2, h2, l2, b2) <= 0:
        return 0.0
    c1 = corners(e1, n1, h1, l1, b1)
    c2 = corners(e2, n2, h2, l2, b2)
    # fix corner 4
    rad = norm360(h1) * math.pi / 180.0
    # corners() will be fixed below
    best = math.inf
    for i in range(4):
        for j in range(4):
            d, _ = point_seg_dist(c1[i], c2[j], c2[(j + 1) % 4])
            best = min(best, d)
            d, _ = point_seg_dist(c2[i], c1[j], c1[(j + 1) % 4])
            best = min(best, d)
    return best


def find_contact(samp_a, samp_b, start, end, precision=0.05, coarse=0.5):
    t = start
    prev = t
    prev_c = sat_clearance(*samp_a(t), *samp_b(t))
    if prev_c <= 0:
        return t
    t += coarse
    while t <= end + 1e-12:
        tt = min(t, end)
        c = sat_clearance(*samp_a(tt), *samp_b(tt))
        if c <= 0:
            lo, hi = prev, tt
            for _ in range(64):
                if hi - lo <= precision:
                    break
                mid = 0.5 * (lo + hi)
                if sat_clearance(*samp_a(mid), *samp_b(mid)) <= 0:
                    hi = mid
                else:
                    lo = mid
            return hi
        prev, prev_c = tt, c
        t += coarse
    return None


def verdict(tc, clearance_m):
    if tc is not None:
        return "Collision"
    if clearance_m < SAFE_M:
        return "NearMiss"
    return "Avoided"


def min_true_clearance(samp_a, samp_b, start, end, step=0.2):
    best_t, best_c, best_d = start, math.inf, math.inf
    t = start
    while t <= end + 1e-9:
        a, b = samp_a(t), samp_b(t)
        # a = (e,n,h,l,b)
        de, dn = b[0] - a[0], b[1] - a[1]
        d = math.hypot(de, dn)
        if d < best_d:
            best_d = d
            best_t = t
            best_c = true_distance(*a, *b)
        t += step
    # refine near best_t
    t0, t1 = max(start, best_t - 2), min(end, best_t + 2)
    t = t0
    while t <= t1 + 1e-9:
        a, b = samp_a(t), samp_b(t)
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        if d < best_d:
            best_d = d
            best_t = t
            best_c = true_distance(*a, *b)
        t += 0.02
    return best_t, best_c, best_d


# ---- Mary / Lily first-principles ----
MARY = Params(K=0.10, T=60.0, u_ref=12.0, max_rudder=35, rudder_rate=2.5, speed_tau=90, loa=120, beam=20)
LILY = Params(K=0.08, T=70.0, u_ref=12.0, max_rudder=35, rudder_rate=2.5, speed_tau=90, loa=98, beam=16)

def straight_track(east0, north0, hdg, speed, start, end, step=1.0):
    rad = hdg * math.pi / 180.0
    sm = speed * MPS_PER_KN
    states = []
    t = start
    while t <= end + 1e-9:
        d = sm * t
        states.append(State(t, east0 + d * math.sin(rad), north0 + d * math.cos(rad), hdg, 0.0, speed, 0.0))
        t += step
    return states


def cf_track(orig: List[State], p: Params, interventions: List[Intervention], diverge: float, end: float, dt=0.1):
    pre = [s for s in orig if s.t < diverge - 1e-9]
    s0 = sample(orig, diverge)
    initial = State(diverge, s0.east, s0.north, s0.psi, 0.0, s0.u, 0.0)
    applicable = [iv for iv in interventions if iv.t_exec >= diverge - 1e-9]
    sim = simulate(initial, p, applicable, end, dt)
    out = list(pre)
    for s in sim:
        if out and s.t <= out[-1].t + 1e-9:
            continue
        out.append(s)
    return out


def eval_pair(a: List[State], pa: Params, b: List[State], pb: Params, start, end):
    def sa(t):
        s = sample(a, t)
        return (s.east, s.north, s.psi, pa.loa, pa.beam)

    def sb(t):
        s = sample(b, t)
        return (s.east, s.north, s.psi, pb.loa, pb.beam)

    tc = find_contact(sa, sb, start, end)
    if tc is not None:
        return {"verdict": "Collision", "tc": tc, "clearance_true": 0.0, "clearance_sat_cpa": 0.0}
    t_cpa, true_c, _ = min_true_clearance(sa, sb, start, end)
    sat_c = sat_clearance(*sa(t_cpa), *sb(t_cpa))
    return {
        "verdict": verdict(None, true_c),
        "verdict_sat": verdict(None, max(sat_c, 0.0)),
        "tc": None,
        "cpa_t": t_cpa,
        "clearance_true": true_c,
        "clearance_sat_cpa": max(sat_c, 0.0),
    }


def run_demo():
    start, end = 0.0, 720.0
    mary0 = straight_track(193.7, -2292.7, 355.0, 8.0, start, end)
    lily0 = straight_track(-267.2, 2795.6, 175.0, 10.0, start, end)

    s0 = eval_pair(mary0, MARY, lily0, LILY, start, end)

    mary_s1 = cf_track(mary0, MARY, [Intervention("turn", 420.0, rudder=15.0, heading_change=15.0)], 420.0, end)
    s1 = eval_pair(mary_s1, MARY, lily0, LILY, start, end)

    mary_s2 = cf_track(mary0, MARY, [Intervention("speed", 300.0, target_speed=6.0)], 300.0, end)
    s2 = eval_pair(mary_s2, MARY, lily0, LILY, start, end)

    lily_s3 = cf_track(lily0, LILY, [Intervention("turn", 480.0, rudder=35.0, heading_change=30.0)], 480.0, end)
    s3 = eval_pair(mary0, MARY, lily_s3, LILY, start, end)

    return {"S0": s0, "S1": s1, "S2": s2, "S3": s3}


def load_dump(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8-sig'))


def samples_to_states(samples):
    return [State(s[0], s[1], s[2], s[3], s[5], s[4], s[6]) for s in samples]


def eval_dumped_scenario(scen):
    tracks = scen["tracks"]
    ids = list(tracks.keys())
    a_id, b_id = ids[0], ids[1]
    ta, tb = tracks[a_id], tracks[b_id]
    sa_states = samples_to_states(ta["samples"])
    sb_states = samples_to_states(tb["samples"])
    pa = Params(K=0.1, T=60, u_ref=12, loa=ta["loaM"], beam=ta["beamM"])
    pb = Params(K=0.1, T=60, u_ref=12, loa=tb["loaM"], beam=tb["beamM"])
    start = min(sa_states[0].t, sb_states[0].t)
    end = min(sa_states[-1].t, sb_states[-1].t)

    def sa(t):
        s = sample(sa_states, t)
        return (s.east, s.north, s.psi, pa.loa, pa.beam)

    def sb(t):
        s = sample(sb_states, t)
        return (s.east, s.north, s.psi, pb.loa, pb.beam)

    tc = find_contact(sa, sb, start, end, precision=0.05, coarse=0.5)
    if tc is not None:
        return {"verdict": "Collision", "tc": tc, "clearance_true": 0.0}
    t_cpa, true_c, _ = min_true_clearance(sa, sb, start, end)
    return {"verdict": verdict(None, true_c), "tc": None, "cpa_t": t_cpa, "clearance_true": true_c,
            "clearance_sat_cpa": max(sat_clearance(*sa(t_cpa), *sb(t_cpa)), 0.0)}


def analyze_yangze_antenna_and_trim(dump):
    """Use dumped S0 tracks: try antenna offsets and post-collision trim effect is in C# tests.
    Here we only scan antenna offset at t=204s and also re-detect contact on dumped track.
    """
    s0 = next(r for r in dump["yangze22"]["results"] if r["id"] == "S0")
    y = s0["tracks"]["yangze22"]
    v = s0["tracks"]["vega_dream"]
    ys, vs = samples_to_states(y["samples"]), samples_to_states(v["samples"])
    loa_y, beam_y = y["loaM"], y["beamM"]
    loa_v, beam_v = v["loaM"], v["beamM"]
    report_t = 204.0

    def shift(s, fwd, loa):
        rad = norm360(s.psi) * math.pi / 180.0
        return State(
            s.t,
            s.east - fwd * math.sin(rad),
            s.north - fwd * math.cos(rad),
            s.psi, s.r, s.u, s.rudder,
        )

    y204, v204 = sample(ys, report_t), sample(vs, report_t)
    base = sat_clearance(y204.east, y204.north, y204.psi, loa_y, beam_y,
                         v204.east, v204.north, v204.psi, loa_v, beam_v)
    grid = []
    best = (base, 0.0, 0.0, False)
    for yf in [-0.40, -0.35, -0.30, -0.25, -0.20, -0.15, -0.10, -0.05, 0.0, 0.10]:
        for vf in [-0.40, -0.35, -0.30, -0.25, -0.20, -0.15, -0.10, -0.05, 0.0, 0.10]:
            yy = shift(y204, yf * loa_y, loa_y)
            vv = shift(v204, vf * loa_v, loa_v)
            c = sat_clearance(yy.east, yy.north, yy.psi, loa_y, beam_y,
                              vv.east, vv.north, vv.psi, loa_v, beam_v)
            hit = c <= 0
            grid.append((yf, vf, c, hit))
            if c < best[0]:
                best = (c, yf, vf, hit)

    # Also: if we hold heading/speed from t=204 onward (drop post-collision motion)
    def hold_after(states, cut):
        s_cut = sample(states, cut)
        out = [s for s in states if s.t <= cut + 1e-9]
        if not out or out[-1].t < cut - 1e-9:
            out.append(s_cut)
        t = cut
        end = states[-1].t
        rad = norm360(s_cut.psi) * math.pi / 180.0
        sm = s_cut.u * MPS_PER_KN
        east, north = s_cut.east, s_cut.north
        while t < end - 1e-9:
            step = min(1.0, end - t)
            east += sm * math.sin(rad) * step
            north += sm * math.cos(rad) * step
            t += step
            out.append(State(t, east, north, s_cut.psi, 0.0, s_cut.u, s_cut.rudder))
        return out

    y_hold = hold_after(ys, report_t)
    v_hold = hold_after(vs, report_t)  # VEGA may already be nearly straight

    def sa(t, sts=y_hold):
        s = sample(sts, t)
        return (s.east, s.north, s.psi, loa_y, beam_y)

    def sb(t, sts=v_hold):
        s = sample(sts, t)
        return (s.east, s.north, s.psi, loa_v, beam_v)

    tc_hold = find_contact(lambda t: sa(t), lambda t: sb(t), 0.0, ys[-1].t)
    angle_hold = None
    if tc_hold is not None:
        ys_ = sample(y_hold, tc_hold)
        vs_ = sample(v_hold, tc_hold)
        d = abs(norm180(ys_.psi - vs_.psi))
        angle_hold = d if d <= 90 else 180 - d

    return {
        "clearance_at_report_t": base,
        "best_offset": {"clearance": best[0], "yangze_fwd_L": best[1], "vega_fwd_L": best[2], "contact": best[3]},
        "offsets_that_contact": [(yf, vf) for yf, vf, c, hit in grid if hit],
        "hold_after_204": {"tc": tc_hold, "angle": angle_hold},
    }


def corners(east, north, hdg, loa, beam):
    rad = norm360(hdg) * math.pi / 180.0
    s, c = math.sin(rad), math.cos(rad)
    fx, fy = s, c
    sx, sy = c, -s
    hl, hb = loa * 0.5, beam * 0.5
    return [
        (east + fx * hl + sx * hb, north + fy * hl + sy * hb),
        (east + fx * hl - sx * hb, north + fy * hl - sy * hb),
        (east - fx * hl - sx * hb, north - fy * hl - sy * hb),
        (east - fx * hl + sx * hb, north - fy * hl + sy * hb),
    ]


def main():
    repo = Path("/workspace/maritime-sim-design")
    logs = repo / "logs"
    logs.mkdir(exist_ok=True)
    demo = run_demo()
    dump_path = logs / "w14-scenario-dump.json"
    dump = load_dump(dump_path)

    lines = []
    lines.append("# W14 独立核算（Python Nomoto RK4 + 独立 OBB）")
    lines.append("")
    lines.append("模型：T·dr/dt + r = K·(u/u_ref)·δ；du/dt = (u_target−u)/τ；舵速限制；RK4；航向 PD（kP=1.2, kD=10）。")
    lines.append("碰撞：分离轴定理（与被测同一判据）二分定位 tc，精度 0.05 s。未碰撞时另算凸多边形真实最小距离。")
    lines.append("")

    announced = {
        "S0": ("Collision", 539.96, None),
        "S1": ("NearMiss", None, 127.6),
        "S2": ("Collision", None, None),
        "S3": ("NearMiss", None, 52.4),
    }
    lines.append("## Mary / Lily（独立从初值积分）")
    lines.append("")
    lines.append("| 情景 | 独立结论 | 独立 tc / 真实净距 | 实施方结论（自报） | 结论是否一致 | 数值偏差 |")
    lines.append("|---|---|---|---|---|---|")
    all_ok = True
    for sid in ("S0", "S1", "S2", "S3"):
        r = demo[sid]
        ann_v, ann_tc, ann_c = announced[sid]
        match = r["verdict"] == ann_v
        if r["verdict"] == "NearMiss" and r.get("verdict_sat") != "NearMiss":
            # true clearance may flip verdict vs SAT-based product
            pass
        # Product uses SAT clearance for verdict. Compare category to product SAT first.
        prod_like = r.get("verdict_sat", r["verdict"]) if r["verdict"] != "Collision" else "Collision"
        match_prod = prod_like == ann_v or r["verdict"] == ann_v
        if not match_prod:
            all_ok = False
        detail = ""
        if r["tc"] is not None:
            detail = f"tc={r['tc']:.2f}s"
            if ann_tc is not None:
                detail += f"（偏差 {r['tc']-ann_tc:+.2f}s）"
        else:
            detail = f"真实净距={r['clearance_true']:.1f}m，SAT净距={r['clearance_sat_cpa']:.1f}m"
            if ann_c is not None:
                detail += f"（相对自报 SAT {r['clearance_sat_cpa']-ann_c:+.1f}m）"
        lines.append(
            f"| {sid} | {r['verdict']}"
            + (f"（按SAT则为{r.get('verdict_sat')}）" if r['verdict'] != "Collision" and r.get('verdict_sat') != r['verdict'] else "")
            + f" | {detail} | {ann_v} | {'是' if match_prod else '否'} | {detail} |"
        )

    if dump:
        lines.append("")
        lines.append("## 与 C# 转储逐项对照")
        lines.append("")
        lines.append("| 案例 | 情景 | C# 结论 | 独立结论（用转储航迹重算碰撞） | tc C# | tc 独立 | 净距 C# (SAT) | 真实净距 | 结论一致 |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for case_name, key in (("Mary/Lily", "demo"), ("YANGZE 22", "yangze22")):
            for scen in dump[key]["results"]:
                indep = eval_dumped_scenario(scen)
                csharp_v = scen["verdict"]
                match = indep["verdict"] == csharp_v or (
                    csharp_v != "Collision" and indep["verdict"] != "Collision"
                    and indep.get("clearance_true", 1) >= 0
                )
                # Strict: verdict category must match C# (C# uses SAT clearance).
                if csharp_v == "Collision":
                    strict = indep["verdict"] == "Collision"
                else:
                    # Recompute SAT-based verdict from dumped tracks
                    sat_v = "Avoided" if indep.get("clearance_true") is not None else indep["verdict"]
                    # Better: use clearance_sat if available when no collision
                    if indep["verdict"] == "Collision":
                        strict = False
                    else:
                        sat_c = indep.get("clearance_sat_cpa", indep.get("clearance_true", 0))
                        sat_v = verdict(None, sat_c)
                        # Wait, verdict() uses true safe distance on given clearance.
                        # For fair compare, use SAT clearance.
                        strict = sat_v == csharp_v
                        # If true-distance flips NearMiss↔Avoided, record it but still check SAT match.
                tc_cs = scen["tcSeconds"]
                tc_in = indep.get("tc")
                tc_cs_s = f"{tc_cs:.2f}" if tc_cs is not None else "—"
                tc_in_s = f"{tc_in:.2f}" if tc_in is not None else "—"
                clr_cs = f"{scen['minClearanceM']:.1f}"
                clr_tr = f"{indep.get('clearance_true', 0):.1f}" if indep["verdict"] != "Collision" else "0"
                if csharp_v == "Collision":
                    ok = indep["verdict"] == "Collision"
                    if ok and tc_cs is not None and tc_in is not None:
                        ok = abs(tc_cs - tc_in) <= 0.11
                else:
                    # independent SAT verdict from dumped track
                    ok = indep["verdict"] != "Collision"
                    # compute SAT verdict
                    # already in indep if no collision
                    sat_c = indep.get("clearance_sat_cpa")
                    if sat_c is not None:
                        ok = verdict(None, sat_c) == csharp_v
                mark = "是" if ok else "否"
                if not ok:
                    all_ok = False
                lines.append(
                    f"| {case_name} | {scen['id']} | {csharp_v} | {indep['verdict']} | {tc_cs_s} | {tc_in_s} | {clr_cs} | {clr_tr} | {mark} |"
                )

        lines.append("")
        lines.append("## YANGZE 22 偏差原因核验")
        lines.append("")
        ana = analyze_yangze_antenna_and_trim(dump)
        lines.append(f"- 报告时刻 t=204 s（22:01:54）按 S0 回放航迹的 SAT 净距：**{ana['clearance_at_report_t']:.1f} m**（未接触，与实施方说明一致）。")
        bo = ana["best_offset"]
        lines.append(
            f"- 天线相对船中心沿首尾线扫描（−0.40L…+0.10L）：最小净距 **{bo['clearance']:.1f} m**，"
            f"出现在 YANGZE 天线={bo['yangze_fwd_L']:+.2f}L、VEGA 天线={bo['vega_fwd_L']:+.2f}L。"
            f"{'此时两船体在报告时刻已经接触。' if bo['contact'] else '在该网格内报告时刻仍未接触。'}"
        )
        if ana["offsets_that_contact"]:
            lines.append(f"- 能使报告时刻接触的偏移组合数：{len(ana['offsets_that_contact'])}（例如前几组 {ana['offsets_that_contact'][:6]}）。")
        else:
            lines.append("- 在该合理网格内，仅天线偏移不足以在 22:01:54 造成接触。")
        h = ana["hold_after_204"]
        if h["tc"] is None:
            lines.append("- 若从 22:01:54 起两船均保向保速（去掉碰撞后 VDR 点对插值的影响）：**不再发生接触**。")
        else:
            late = h["tc"] - 204.0
            ang = "—" if h["angle"] is None else f"{h['angle']:.1f}°"
            lines.append(
                f"- 若从 22:01:54 起两船保向保速：仍在 t={h['tc']:.2f}s（22:01:54 之后 {late:.1f}s）接触，碰撞角 {ang}。"
            )
        s0 = next(r for r in dump["yangze22"]["results"] if r["id"] == "S0")
        lines.append(f"- C# S0：tc={s0['tcSeconds']:.2f}s（{s0['tcLocal']}），碰撞角 {s0['geometry']['angleDeg']:.1f}°，距船首 {s0['geometry']['fromBowM']:.0f} m。")
        lines.append(f"- 实施方偏差说明原文：{dump['yangze22']['originalDeviation']}")

    lines.append("")
    lines.append(f"独立核算结论类别与实施方一致：{'是' if all_ok else '有不一致，见上表'}。")
    text = "\n".join(lines) + "\n"
    out = logs / "w14-independent-check.md"
    out.write_text(text, encoding="utf-8")
    # machine-readable
    (logs / "w14-independent-check.json").write_text(
        json.dumps({"demo": demo, "all_ok": all_ok}, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(text)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
