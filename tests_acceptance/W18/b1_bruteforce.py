#!/usr/bin/env python3
"""Independent check of STCW 24h rest-total / split / longest-rest for W18.

Modes
-----
clipped (default, ruling: 总量规则 / 严格任意窗口)
    Scan every minute-aligned 24h window fully inside the record.
    Rest truncated by the window is counted by in-window length.

fullsegment (ruling 21:25: 拆分规则 / 完整休息段)
    Only evaluate 24h windows whose start is a rest-segment start or end
    clipped into [recordStart, recordEnd-24h], plus recordStart and
    recordEnd-24h. Intersecting rest segments are counted by full length
    (not window-clipped). With --optimistic, a segment touching a record
    edge is treated as long enough (window length).

Input JSON (stdin or --file): recordStart/recordEnd ISO-8601,
rest: [[start,end],...]. Batch: { "cases": [ {...}, ... ] }.
Output JSON to stdout.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone


def parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def iso(t: datetime) -> str:
    return t.isoformat()


def hours_between(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds() / 3600.0


def clip_segments(rests, w0, w1):
    segs = []
    for a, b in rests:
        lo = max(a, w0)
        hi = min(b, w1)
        if hi > lo:
            segs.append((lo, hi, (hi - lo).total_seconds()))
    return segs


def eval_clipped(data):
    rec0 = parse(data["recordStart"])
    rec1 = parse(data["recordEnd"])
    rests = [(parse(a), parse(b)) for a, b in data["rest"]]
    window = timedelta(hours=float(data.get("windowHours", 24)))
    min_rest = float(data.get("minRestHours", 10)) * 3600
    min_longest = float(data.get("minLongestHours", 6)) * 3600
    max_periods = int(data.get("maxPeriods", 2))
    step = timedelta(seconds=int(data.get("stepSeconds", 60)))

    last = rec1 - window
    viol = {"Rest24h": [], "LongestRest": [], "RestSplit": []}
    t = rec0
    while t <= last:
        segs = clip_segments(rests, t, t + window)
        total = sum(s[2] for s in segs)
        lengths = sorted((s[2] for s in segs), reverse=True)
        longest = lengths[0] if lengths else 0.0
        topn = sum(lengths[:max_periods])
        flags = []
        if total < min_rest - 1e-9:
            flags.append("Rest24h")
        if segs and longest < min_longest - 1e-9:
            flags.append("LongestRest")
        if total >= min_rest - 1e-9 and topn < min_rest - 1e-9:
            flags.append("RestSplit")
        rec = {
            "start": iso(t),
            "end": iso(t + window),
            "startHours": hours_between(rec0, t),
            "totalRestHours": total / 3600.0,
            "longestHours": longest / 3600.0,
            "topNHours": topn / 3600.0,
            "periods": len(segs),
            "violations": flags,
        }
        for f in flags:
            viol[f].append(rec)
        t += step

    out = {
        "mode": "clipped",
        "windowCount": int(((last - rec0) / step) + 1) if last >= rec0 else 0,
        "violationCounts": {k: len(v) for k, v in viol.items()},
        "first": {k: (v[0] if v else None) for k, v in viol.items()},
        "covers27h": any(
            abs((parse(r["start"]) - (rec0 + timedelta(hours=27))).total_seconds()) < 1
            for r in viol["LongestRest"]
        ),
        "longestAt27": next(
            (
                r
                for r in viol["LongestRest"]
                if abs((parse(r["start"]) - (rec0 + timedelta(hours=27))).total_seconds()) < 1
            ),
            None,
        ),
        "clippedAt27": next(
            (
                r
                for r in (viol["LongestRest"] + viol["RestSplit"] + viol["Rest24h"])
                if abs((parse(r["start"]) - (rec0 + timedelta(hours=27))).total_seconds()) < 1
            ),
            _clipped_at(rec0, rests, window, min_rest, min_longest, max_periods, 27.0),
        ),
        "sampleLongestRest": viol["LongestRest"][:3],
        "sampleRestSplit": viol["RestSplit"][:3],
        "allLongestStartsHours": [
            (parse(r["start"]) - rec0).total_seconds() / 3600.0 for r in viol["LongestRest"]
        ],
        "rest24hStartsHours": [
            (parse(r["start"]) - rec0).total_seconds() / 3600.0 for r in viol["Rest24h"]
        ],
    }
    return out


def _clipped_at(rec0, rests, window, min_rest, min_longest, max_periods, hours):
    t = rec0 + timedelta(hours=hours)
    segs = clip_segments(rests, t, t + window)
    total = sum(s[2] for s in segs)
    lengths = sorted((s[2] for s in segs), reverse=True)
    longest = lengths[0] if lengths else 0.0
    topn = sum(lengths[:max_periods])
    flags = []
    if total < min_rest - 1e-9:
        flags.append("Rest24h")
    if segs and longest < min_longest - 1e-9:
        flags.append("LongestRest")
    if total >= min_rest - 1e-9 and topn < min_rest - 1e-9:
        flags.append("RestSplit")
    return {
        "start": iso(t),
        "end": iso(t + window),
        "startHours": hours,
        "totalRestHours": total / 3600.0,
        "longestHours": longest / 3600.0,
        "topNHours": topn / 3600.0,
        "periods": len(segs),
        "violations": flags,
    }


def aligned_starts(rec0, rec1, rests, window):
    last = rec1 - window
    if last < rec0:
        return [], last
    starts = {rec0, last}
    for a, b in rests:
        for t in (a, b):
            if t < rec0:
                t = rec0
            if t > last:
                t = last
            starts.add(t)
    return sorted(starts), last


def segment_length(a, b, rec0, rec1, window, optimistic):
    if optimistic and (a <= rec0 or b >= rec1):
        return window.total_seconds()
    return (b - a).total_seconds()


def eval_fullsegment(data, optimistic=False):
    rec0 = parse(data["recordStart"])
    rec1 = parse(data["recordEnd"])
    rests = [(parse(a), parse(b)) for a, b in data["rest"]]
    rests = sorted(rests, key=lambda p: p[0])
    window = timedelta(hours=float(data.get("windowHours", 24)))
    min_rest = float(data.get("minRestHours", 10)) * 3600
    min_longest = float(data.get("minLongestHours", 6)) * 3600
    max_periods = int(data.get("maxPeriods", 2))
    max_interval = float(data.get("maxIntervalHours", 14)) * 3600

    starts, last = aligned_starts(rec0, rec1, rests, window)
    has_rest = len(rests) > 0
    windows = []
    viol = {"LongestRest": [], "RestSplit": []}
    for t in starts:
        w1 = t + window
        lens = []
        for a, b in rests:
            if b <= t or a >= w1:
                continue
            lens.append(segment_length(a, b, rec0, rec1, window, optimistic))
        lens.sort(reverse=True)
        total = sum(lens)
        longest = lens[0] if lens else 0.0
        topn = sum(lens[:max_periods])
        flags = []
        if has_rest and longest < min_longest - 1e-9:
            flags.append("LongestRest")
        if total >= min_rest - 1e-9 and topn < min_rest - 1e-9:
            flags.append("RestSplit")
        rec = {
            "start": iso(t),
            "end": iso(w1),
            "startHours": hours_between(rec0, t),
            "isRecordStart": abs((t - rec0).total_seconds()) < 1e-9,
            "isRecordEndMinusWindow": abs((t - last).total_seconds()) < 1e-9,
            "totalRestHours": total / 3600.0,
            "longestHours": longest / 3600.0,
            "topNHours": topn / 3600.0,
            "periods": len(lens),
            "violations": flags,
        }
        windows.append(rec)
        for f in flags:
            viol[f].append(rec)

    intervals = []
    for (a0, b0), (a1, b1) in zip(rests, rests[1:]):
        gap = (a1 - b0).total_seconds()
        if gap > max_interval + 1e-9:
            intervals.append(
                {
                    "from": iso(b0),
                    "to": iso(a1),
                    "gapHours": gap / 3600.0,
                    "limitHours": max_interval / 3600.0,
                }
            )

    def at_hours(h):
        target = rec0 + timedelta(hours=h)
        return next(
            (w for w in windows if abs((parse(w["start"]) - target).total_seconds()) < 1),
            None,
        )

    return {
        "mode": "fullsegment",
        "optimistic": optimistic,
        "alignedCount": len(starts),
        "alignedStartsHours": [hours_between(rec0, t) for t in starts],
        "windows": windows,
        "violationCounts": {k: len(v) for k, v in viol.items()},
        "longestRestStartsHours": [w["startHours"] for w in viol["LongestRest"]],
        "restSplitStartsHours": [w["startHours"] for w in viol["RestSplit"]],
        "intervals": intervals,
        "covers27h": at_hours(27.0) is not None and "LongestRest" in (at_hours(27.0) or {}).get("violations", []),
        "windowAt27": at_hours(27.0),
        "windowAt24h01m": at_hours(24.0 + 1.0 / 60.0),
        "recordStartWindow": next((w for w in windows if w["isRecordStart"]), None),
        "recordEndMinus24hWindow": next((w for w in windows if w["isRecordEndMinusWindow"]), None),
    }


def eval_case(data, mode, optimistic):
    if mode == "fullsegment":
        # Always emit both views so a single call can be compared with
        # C# Violations (optimistic) and InsufficientData (pessimistic-only).
        if "optimistic" in data or optimistic:
            want = bool(data.get("optimistic", optimistic))
            return eval_fullsegment(data, optimistic=want)
        out = {
            "mode": "fullsegment",
            "pessimistic": eval_fullsegment(data, optimistic=False),
            "optimistic": eval_fullsegment(data, optimistic=True),
        }
        # Keep single-case convenience keys on the pessimistic view for the
        # original B1 schedule (no edge-truncated rests in the 27h window).
        for k in (
            "covers27h",
            "windowAt27",
            "windowAt24h01m",
            "alignedStartsHours",
            "violationCounts",
            "alignedCount",
        ):
            out[k] = out["pessimistic"][k]
        return out
    return eval_clipped(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--mode", choices=("clipped", "fullsegment"), default="clipped")
    ap.add_argument("--optimistic", action="store_true")
    args = ap.parse_args()
    raw = open(args.file, "r", encoding="utf-8").read() if args.file else sys.stdin.read()
    data = json.loads(raw)
    if isinstance(data, dict) and "cases" in data:
        mode = data.get("mode", args.mode)
        out = {
            "mode": mode,
            "caseCount": len(data["cases"]),
            "cases": [eval_case(c, c.get("mode", mode), bool(c.get("optimistic", args.optimistic))) for c in data["cases"]],
        }
    else:
        out = eval_case(data, data.get("mode", args.mode), bool(data.get("optimistic", args.optimistic)))
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
