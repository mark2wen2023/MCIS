#!/usr/bin/env python3
"""Independent kinematics + CPA + heading-stability calculation for
TimeBands_MultipleTransitions. Does not call or import the C# engine.

Ship model matches tests_acceptance/W1/W1AccFixture.cs:
  1 s midpoint integration, turn rate 6 deg/s, shortest-turn Delta,
  output every 10 s (and also keep 1 s truth).
Risk: DCPA < 1 nm and 0 < TCPA <= 720 s.
Heading stable: peak-to-peak signed heading excursion in the trailing
60 s window <= 5 deg (ruling D12). Also report |h(t)-h(t-60)|.
Head-on: heading difference from reciprocal <= 6 deg AND either view
has the other ship within 22.5 deg of the bow (15 deg = no doubt).
"""
import math, os, sys

NM = 1852.0
OUT = "/workspace/maritime-sim-design/logs/w1.1-retest-transitions-calc.txt"

def sind(d): return math.sin(d * math.pi / 180.0)
def cosd(d): return math.cos(d * math.pi / 180.0)
def norm(a): return (a % 360.0 + 360.0) % 360.0
def delta(frm, to): return norm(to - frm + 180.0) - 180.0

def simulate(e0, n0, h0, v0, orders, duration, dt=1.0, turn_rate=6.0, accel=0.5):
    """orders: list of (t, hdg). Returns list of dicts at every dt."""
    e, n, h, v = e0, n0, h0, v0
    cmd_h, cmd_v = h0, v0
    orders = sorted(orders)
    oi = 0
    steps = int(round(duration / dt))
    out = []
    for k in range(steps + 1):
        t = k * dt
        while oi < len(orders) and orders[oi][0] <= t + 1e-9:
            cmd_h = orders[oi][1]
            oi += 1
        out.append(dict(t=t, e=e, n=n, h=norm(h), v=v,
                        ve=v * sind(h), vn=v * cosd(h)))
        d = delta(h, cmd_h)
        step = min(abs(d), turn_rate * dt) * (1 if d >= 0 else -1)
        # midpoint integration as in Ship.Run
        h_new = norm(h + step)
        hm = h + step / 2.0
        vm = v  # no speed change
        e += vm * sind(hm) * dt
        n += vm * cosd(hm) * dt
        h = h_new
    return out

def cpa(own, tgt):
    re, rn = tgt["e"] - own["e"], tgt["n"] - own["n"]
    ve, vn = tgt["ve"] - own["ve"], tgt["vn"] - own["vn"]
    r2 = re * re + rn * rn
    v2 = ve * ve + vn * vn
    dist = math.sqrt(r2)
    if v2 <= 1e-18:
        return dict(dcpa_m=dist, tcpa=0.0, dist=dist, deg=True, div=False, dcpa_nm=dist / NM)
    tcpa = -(re * ve + rn * vn) / v2
    cpe, cpn = re + ve * tcpa, rn + vn * tcpa
    dcpa = math.sqrt(cpe * cpe + cpn * cpn)
    closing = (re * ve + rn * vn) < 0
    return dict(dcpa_m=dcpa, tcpa=tcpa, dist=dist, deg=False, div=not closing, dcpa_nm=dcpa / NM)

def bearing_of(observer, target):
    """Relative bearing of target as seen from observer (deg, 0=bow, 90=stbd)."""
    re, rn = target["e"] - observer["e"], target["n"] - observer["n"]
    true_brg = norm(math.atan2(re, rn) * 180.0 / math.pi)
    return norm(true_brg - observer["h"])

def heading_range(hist, t, window=60.0):
    """Peak-to-peak signed excursion over (t-window, t] using 1 s samples."""
    start = t - window
    pts = [p for p in hist if start - 1e-9 <= p["t"] <= t + 1e-9]
    if not pts:
        return 0.0, 0.0
    # interpolate start if needed
    cum = 0.0
    mn = mx = 0.0
    prev = pts[0]["h"]
    # if first sample is after start, still start from first available (no history)
    for p in pts[1:]:
        cum += delta(prev, p["h"])
        mn = min(mn, cum)
        mx = max(mx, cum)
        prev = p["h"]
    net = abs(delta(pts[0]["h"], pts[-1]["h"]))
    return mx - mn, net

def risk(c):
    return (not c["deg"]) and (c["tcpa"] > 0) and (c["tcpa"] <= 720.0) and (c["dcpa_nm"] < 1.0)

def classify(own, tgt):
    obrg = bearing_of(own, tgt)
    tbrg = bearing_of(tgt, own)
    # difference from reciprocal: how close |hdg_own - hdg_tgt| is to 180
    hdg_abs = abs(delta(own["h"], tgt["h"]))
    from_recip = abs(180.0 - hdg_abs)
    def fwd(brg, half):
        return abs(delta(0.0, brg)) <= half + 1e-9
    head_on = from_recip <= 6.0 + 1e-9 and (fwd(obrg, 22.5) or fwd(tbrg, 22.5))
    doubt = head_on and (not fwd(obrg, 15.0)) and (not fwd(tbrg, 15.0))
    if head_on:
        return "HeadOn", doubt, obrg, tbrg, from_recip
    # overtaking: other in own's stern sector (>=112.5 and <=247.5) or vice versa
    def in_stern(brg):
        return 112.5 - 1e-9 <= brg <= 247.5 + 1e-9
    if in_stern(obrg) or in_stern(tbrg):
        return "Overtaking", False, obrg, tbrg, from_recip
    return "Crossing", False, obrg, tbrg, from_recip

def main():
    own_1s = simulate(0, 0, 0, 5, [], 900)
    tgt_1s = simulate(30, -1000, 0, 10, [(500, 180)], 900)
    own_by_t = {round(p["t"], 6): p for p in own_1s}
    tgt_by_t = {round(p["t"], 6): p for p in tgt_1s}

    lines = []
    def log(s=""):
        lines.append(s)
        print(s)

    log("W1.1 independent calculation for TimeBands_MultipleTransitions")
    log("own: (0,0) hdg 0 deg 5 m/s constant")
    log("tgt: (30,-1000) hdg 0 deg 10 m/s; at t=500 s turn to 180 deg at 6 deg/s, shortest path")
    d0 = delta(0, 180)
    log(f"shortest-turn Delta(0,180) = {d0:.1f} deg  => {'port' if d0 < 0 else 'starboard'}")
    log(f"turn duration = {abs(d0)/6.0:.1f} s, completes at t = {500 + abs(d0)/6.0:.1f} s")
    # verify heading at key times
    for t in (0, 500, 510, 520, 529, 530, 590):
        log(f"  tgt heading at {t:g} s = {tgt_by_t[t]['h']:.4f} deg, pos=({tgt_by_t[t]['e']:.3f}, {tgt_by_t[t]['n']:.3f})")
    log()

    # CPA of first overtaking leg (constant velocity)
    c0 = cpa(own_by_t[0], tgt_by_t[0])
    log(f"initial CPA: DCPA={c0['dcpa_m']:.3f} m ({c0['dcpa_nm']:.4f} nm), TCPA={c0['tcpa']:.3f} s")
    # clear: diverging and distance >= 0.5 nm
    clear_t_1s = None
    first_risk_after_clear_1s = None
    cpa_t = None
    rows_1s = []
    prev_clear = False
    for t in range(0, 901):
        o, g = own_by_t[t], tgt_by_t[t]
        c = cpa(o, g)
        rk = risk(c)
        cl = c["div"] and c["dist"] >= 0.5 * NM
        if cpa_t is None and t > 0:
            prev = cpa(own_by_t[t-1], tgt_by_t[t-1])
            if prev["tcpa"] > 0 and c["tcpa"] <= 0:
                cpa_t = t - 1 + prev["tcpa"] / (prev["tcpa"] - c["tcpa"] + 1e-15) if False else t
        if clear_t_1s is None and cl and t >= 200:
            clear_t_1s = t
        if clear_t_1s is not None and t >= clear_t_1s and rk and first_risk_after_clear_1s is None:
            first_risk_after_clear_1s = t
        rows_1s.append((t, c, rk, cl))

    # more precise clear crossing by interpolation at 1s (first sample where clear)
    # also solve distance = 0.5 nm after CPA analytically on the first (constant) leg
    # after CPA at 200s, rel n = 5*(t-200), dist=sqrt(30^2 + (5*(t-200))^2)
    # 0.5 nm = 926 m; 5*(t-200) = sqrt(926^2 - 30^2)
    half = 0.5 * NM
    dn = math.sqrt(max(0, half * half - 30 * 30))
    clear_exact = 200.0 + dn / 5.0
    log(f"overtaking CPA time ≈ 200 s; distance reaches 0.5 nm at t = {clear_exact:.3f} s (1 s first clear flag at {clear_t_1s})")
    log()

    log(f"first new risk after clear (1 s truth): t = {first_risk_after_clear_1s} s")
    if first_risk_after_clear_1s is not None:
        t = first_risk_after_clear_1s
        c = cpa(own_by_t[t], tgt_by_t[t])
        sit, doubt, obrg, tbrg, recip = classify(own_by_t[t], tgt_by_t[t])
        pr, net = heading_range(tgt_1s, t)
        log(f"  at {t} s: DCPA={c['dcpa_nm']:.4f} nm TCPA={c['tcpa']:.3f} s dist={c['dist']/NM:.4f} nm")
        log(f"  ownBrg={obrg:.2f} tgtBrg={tbrg:.2f} fromRecip={recip:.2f} class={sit} doubt={doubt}")
        log(f"  tgt heading={tgt_by_t[t]['h']:.2f}  60s peak-to-peak={pr:.2f} deg  |net|={net:.2f} deg  stable={pr<=5}")

    # also check a few seconds before
    log("risk around first formation (1 s):")
    for t in range(first_risk_after_clear_1s - 5, first_risk_after_clear_1s + 6):
        c = cpa(own_by_t[t], tgt_by_t[t])
        sit, doubt, obrg, tbrg, recip = classify(own_by_t[t], tgt_by_t[t])
        pr, net = heading_range(tgt_1s, t)
        log(f"  t={t:4d} tgtH={tgt_by_t[t]['h']:7.2f} DCPA={c['dcpa_nm']:.4f} TCPA={c['tcpa']:7.2f} "
            f"R={c['dist']/NM:.3f} risk={str(risk(c)):5s} class={sit:11s} p2p={pr:6.2f} stable={str(pr<=5):5s} "
            f"ownBrg={obrg:6.1f} tgtBrg={tbrg:6.1f}")

    log()
    log("heading stability of target (1 s), around turn end and +60 s:")
    first_stable_after_risk = None
    for t in range(first_risk_after_clear_1s, 641):
        pr, net = heading_range(tgt_1s, t)
        own_pr, _ = heading_range(own_1s, t)
        both = pr <= 5 and own_pr <= 5
        if both and first_stable_after_risk is None:
            first_stable_after_risk = t
        if t in (520, 529, 530, 531, 540, 560, 580, 585, 588, 589, 590, 591, 600) or t == first_stable_after_risk:
            log(f"  t={t:4d} tgtH={tgt_by_t[t]['h']:7.2f} p2p={pr:7.3f} net={net:7.3f} own_p2p={own_pr:.3f} both_stable={both}")
    log(f"first time both headings stable after risk (1 s): t = {first_stable_after_risk} s")
    timeout = first_risk_after_clear_1s + 120
    log(f"120 s timeout would be t = {timeout} s; lock-by-stable happens before timeout: {first_stable_after_risk < timeout}")

    # 10 s sample grid (what the acceptance fixture emits and the engine evaluates,
    # plus interpolation only if the engine inserts extra times — default grid is 10 s
    # and track samples are 10 s, so frames are at 0,10,...,900).
    log()
    log("10 s sample grid:")
    first_risk_10 = None
    first_stable_10 = None
    clear_10 = None
    tcpa_zero_10 = None
    prev_risk = False
    for t in range(0, 901, 10):
        o, g = own_by_t[t], tgt_by_t[t]
        c = cpa(o, g)
        rk = risk(c)
        cl = c["div"] and c["dist"] >= 0.5 * NM
        pr, net = heading_range(tgt_1s, t)  # truth window; also compute from 10 s samples below
        sit, doubt, obrg, tbrg, recip = classify(o, g)
        if clear_10 is None and cl and t >= 200:
            clear_10 = t
        if clear_10 is not None and t >= clear_10 and rk and first_risk_10 is None:
            first_risk_10 = t
        if first_risk_10 is not None and first_stable_10 is None and pr <= 5:
            first_stable_10 = t
        if prev_risk and not rk and t >= (first_risk_10 or 0) and tcpa_zero_10 is None:
            tcpa_zero_10 = t
        prev_risk = rk
        if t >= 370 and t <= 640:
            log(f"  t={t:4d} tgtH={g['h']:7.2f} DCPA={c['dcpa_nm']:.4f} TCPA={c['tcpa']:7.1f} "
                f"R={c['dist']/NM:.3f} risk={str(rk):5s} clear={str(cl):5s} class={sit:11s} "
                f"doubt={str(doubt):5s} p2p={pr:6.2f} stable={pr<=5} "
                f"ownBrg={obrg:6.1f} tgtBrg={tbrg:6.1f} recip={recip:.2f}")

    # stability using ONLY 10 s sampled headings (peak-to-peak over samples in window)
    def heading_range_10(hist, t, window=60.0):
        pts = [p for p in hist if (t - window) - 1e-9 <= p["t"] <= t + 1e-9 and abs(p["t"]/10 - round(p["t"]/10)) < 1e-9]
        # include interpolated start
        # use 10s points only, plus exact t and t-window if we interpolate heading
        samples = [p for p in hist if abs(p["t"] % 10) < 1e-9 or abs(p["t"] % 10 - 10) < 1e-9]
        win = [p for p in samples if t - window - 1e-9 <= p["t"] <= t + 1e-9]
        if not win:
            return 0.0
        cum = mn = mx = 0.0
        prev = win[0]["h"]
        for p in win[1:]:
            cum += delta(prev, p["h"])
            mn = min(mn, cum); mx = max(mx, cum); prev = p["h"]
        return mx - mn

    log()
    log("stability from 10 s samples only (plus 1 s truth p2p already above):")
    first_stable_10s_samples = None
    for t in range(first_risk_10, 641, 10):
        p10 = heading_range_10(tgt_1s, t)
        if p10 <= 5 and first_stable_10s_samples is None:
            first_stable_10s_samples = t
        log(f"  t={t:4d} p2p_from_10s_samples={p10:.3f} stable={p10<=5}")
    log(f"first stable on 10 s grid (1 s p2p at those instants): {first_stable_10}")
    log(f"first stable using only 10 s sample headings: {first_stable_10s_samples}")

    # TCPA zero at 1 s after second risk
    zero_1s = None
    for t in range(first_risk_after_clear_1s, 901):
        c = cpa(own_by_t[t], tgt_by_t[t])
        if c["tcpa"] <= 0:
            # interpolate
            prev = cpa(own_by_t[t-1], tgt_by_t[t-1])
            frac = prev["tcpa"] / (prev["tcpa"] - c["tcpa"])
            zero_1s = (t - 1) + frac
            break
    log()
    log(f"second-risk TCPA zero (1 s interp) t = {zero_1s:.3f} s; 10 s first non-risk after lock: {tcpa_zero_10}")
    # geometry at lock time
    tlock = first_stable_after_risk
    o, g = own_by_t[tlock], tgt_by_t[tlock]
    c = cpa(o, g)
    sit, doubt, obrg, tbrg, recip = classify(o, g)
    log(f"geometry at independent lock time {tlock} s: class={sit} doubt={doubt} "
        f"ownBrg={obrg:.2f} tgtBrg={tbrg:.2f} fromRecip={recip:.3f} "
        f"DCPA={c['dcpa_nm']:.4f} TCPA={c['tcpa']:.2f} ownH={o['h']:.2f} tgtH={g['h']:.2f}")

    log()
    log("CONCLUSION")
    log(f"  turn completes at 530.0 s (port 180 deg at 6 deg/s)")
    log(f"  first new risk (1 s) at {first_risk_after_clear_1s} s; (10 s grid) at {first_risk_10} s")
    log(f"  both headings first stable (1 s) at {first_stable_after_risk} s")
    log(f"  both headings first stable (10 s grid) at {first_stable_10s_samples} s")
    log(f"  120 s timeout at {first_risk_after_clear_1s + 120} s (1 s) / {first_risk_10 + 120} s (10 s); not reached")
    log(f"  lock geometry: {sit}")
    log(f"  expected bands: Overtaking until clear (~{clear_exact:.1f} s, 10 s grid {clear_10} s) "
        f"-> NoRisk -> Undetermined [{first_risk_10}, {first_stable_10s_samples}) "
        f"-> HeadOn until TCPA zero (~{zero_1s:.1f} s, 10 s grid {tcpa_zero_10} s) -> NoRisk")

    with open(OUT, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nwrote {OUT}", file=sys.stderr)

if __name__ == "__main__":
    main()
