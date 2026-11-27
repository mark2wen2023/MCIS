"""Request-time authorized snapshot assembly. Pins stay on the server."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SIBLING = Path(__file__).resolve().parent.parent / "w12-registered-json-gap"
sys.path.insert(0, str(SIBLING))

from materialize import SHA_A, SHA_B, require_sha  # noqa: E402
from snapshot import (  # noqa: E402
    CORE_TIMES,
    EXPECTED_CORE,
    QUERIES,
    VESSEL_A,
    VESSEL_B,
    FrozenWorld,
    almost,
    build_analysis_case,
    classify_pair,
    pair_payload,
    run_core,
    utc_of,
    ORIGIN,
)

CASE_TITLE = "Synthetic registered JSON gap"


def register_locked_pair(world: FrozenWorld, fixtures: Path) -> tuple[str, list[dict[str, str]]]:
    raw_a = (fixtures / "vessel-a.json").read_bytes()
    raw_b = (fixtures / "vessel-b.json").read_bytes()
    require_sha(fixtures / "vessel-a.json", SHA_A, "vessel-a.json")
    require_sha(fixtures / "vessel-b.json", SHA_B, "vessel-b.json")
    cid = json.loads(raw_a)["caseId"]
    if cid != json.loads(raw_b)["caseId"]:
        raise RuntimeError("A/B caseId mismatch")
    world.ensure_case(cid, CASE_TITLE)
    pin_a = world.register_bytes(cid, "vessel-a.json", raw_a)
    pin_b = world.register_bytes(cid, "vessel-b.json", raw_b)
    if pin_a["sourceSha256"] != SHA_A or pin_b["sourceSha256"] != SHA_B:
        raise RuntimeError("registered sourceSha256 is not the locked 2048c60 digest")
    return cid, [pin_a, pin_b]


def assemble_authorized_view(
    world: FrozenWorld,
    *,
    case_id: str,
    pins: list[dict[str, str]],
    core_cmd: Path,
    worktree: Path,
    dll_sha: str,
) -> dict[str, Any]:
    """Call frozen _load_registered_pair in the caller's request and return one authorized view only."""
    before = world.counts(case_id)
    items = world.load_pair(case_id, pins, "Synthetic request-time authorized snapshot")
    after = world.counts(case_id)
    delta = after["access"] - before["access"]
    if delta != 2:
        raise RuntimeError(f"expected dual Access on this request, before={before} after={after}")
    statuses = [classify_pair(world, items, t) for t in QUERIES]
    by_t = {row["t"]: row for row in statuses}
    if not (by_t[120.0]["cotemporalMeasured"] and by_t[130.0]["cotemporalMeasured"]):
        raise RuntimeError("T+120/T+130 are not cotemporal measured")
    core_by_t: dict[float, dict[str, Any]] = {}
    core_calls = []
    core_version = "unknown"
    for t in CORE_TIMES:
        payload = {"origin": ORIGIN, "pairs": [pair_payload(by_t[t], items)]}
        env = run_core(core_cmd, worktree, payload)
        results = (env.get("result") or {}).get("results") or []
        if not results:
            raise RuntimeError(f"no core results at T+{t}")
        row = results[0]
        exp = EXPECTED_CORE[t]
        for key, value in exp.items():
            if key == "riskLevel":
                if row.get(key) != value:
                    raise RuntimeError(f"T+{t} {key} {row.get(key)!r} != {value!r}")
            elif not almost(row.get(key), value):
                raise RuntimeError(f"T+{t} {key} {row.get(key)!r} != d49a691 {value!r}")
        core_by_t[t] = {k: row[k] for k in ("currentDistanceNm", "dcpaNm", "tcpaMin", "riskLevel")}
        core_version = env.get("coreVersion") or core_version
        core_calls.append({
            "t": t, "queryUtc": utc_of(t), "coreVersion": env.get("coreVersion"),
            "recalculatedIdentical": True, "result": row,
        })
    pins_by_vessel = {VESSEL_A: pins[0], VESSEL_B: pins[1]}
    view = build_analysis_case(items, pins_by_vessel, statuses, core_by_t, dll_sha, core_version)
    return {
        "ok": True,
        "view": view,
        "sampleStatus": statuses,
        "coreCalls": core_calls,
        "coreVersion": core_version,
        "dllSha256": dll_sha,
        "declaredOpenGaps": view["declaredOpenGaps"],
        "accessBefore": before,
        "accessAfter": after,
        "deltaAccess": delta,
    }
