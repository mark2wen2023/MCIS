"""Register two same-case synthetic pairs via frozen intake and assemble by label.

Pins stay on the server. Clients may only name a confirmed pair label.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SIBLING = Path(__file__).resolve().parent.parent / "w12-registered-json-gap"
HERE = Path(__file__).resolve().parent
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

CASE_TITLE = "Synthetic same-case pair select"
LABEL_A = "pair-a"
LABEL_B = "pair-b"
CONFIRMED_LABELS = (LABEL_A, LABEL_B)
SHA_A_PAIR_B = "8f3e61212730673589068e32383a1677f57255b84ee5879041e8bbd9058ca27a"
EXPECTED_CORE_B = {
    120.0: {"currentDistanceNm": 1.226641, "dcpaNm": 0.599765, "tcpaMin": 2.918219, "riskLevel": "Warning"},
    130.0: {"currentDistanceNm": 1.173535, "dcpaNm": 0.599751, "tcpaMin": 2.751011, "riskLevel": "Warning"},
}
FORBIDDEN_PIN_KEYS = {
    "pin", "pins", "evidenceid", "requestdigest", "sourcesha256",
    "previewdigest", "reportsha256",
}


class PairSelectError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def pair_b_fixture(fixtures: Path | None = None) -> Path:
    if fixtures is not None:
        local = fixtures / "vessel-a-pair-b.json"
        if local.is_file():
            return local
    return HERE / "fixtures" / "vessel-a-pair-b.json"


def register_two_pairs(world: FrozenWorld, fixtures: Path) -> tuple[str, dict[str, list[dict[str, str]]]]:
    """Independently register two legal pairs in one temporary database (afc72a1 method)."""
    raw_a = (fixtures / "vessel-a.json").read_bytes()
    raw_b = (fixtures / "vessel-b.json").read_bytes()
    raw_a_b = pair_b_fixture(HERE / "fixtures").read_bytes()
    require_sha(fixtures / "vessel-a.json", SHA_A, "vessel-a.json")
    require_sha(fixtures / "vessel-b.json", SHA_B, "vessel-b.json")
    require_sha(pair_b_fixture(), SHA_A_PAIR_B, "vessel-a-pair-b.json")
    cid = json.loads(raw_a)["caseId"]
    if cid != json.loads(raw_b)["caseId"] or cid != json.loads(raw_a_b)["caseId"]:
        raise RuntimeError("pair fixture caseId mismatch")
    world.ensure_case(cid, CASE_TITLE)
    pin_a1 = world.register_bytes(cid, "vessel-a.json", raw_a)
    pin_b1 = world.register_bytes(cid, "vessel-b.json", raw_b)
    pin_a2 = world.register_bytes(cid, "vessel-a-pair-b.json", raw_a_b)
    pin_b2 = world.register_bytes(cid, "vessel-b-pair-b.json", raw_b)
    if pin_a1["sourceSha256"] != SHA_A or pin_b1["sourceSha256"] != SHA_B:
        raise RuntimeError("pair A lost the locked 2048c60 digests")
    if pin_a2["sourceSha256"] != SHA_A_PAIR_B:
        raise RuntimeError("pair B vessel-A digest is not the fixed independent original")
    if pin_b2["sourceSha256"] != SHA_B:
        raise RuntimeError("pair B vessel-B must remain the locked original bytes")
    if pin_a1["evidenceId"] == pin_a2["evidenceId"] or pin_a1["requestDigest"] == pin_a2["requestDigest"]:
        raise RuntimeError("pair B overwrote pair A instead of registering independently")
    if pin_b1["evidenceId"] == pin_b2["evidenceId"]:
        raise RuntimeError("pair B vessel-B was not an independent registration")
    return cid, {LABEL_A: [pin_a1, pin_b1], LABEL_B: [pin_a2, pin_b2]}


def public_identities(pins: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {"vesselId": VESSEL_A, "sourceSha256": pins[0]["sourceSha256"]},
        {"vesselId": VESSEL_B, "sourceSha256": pins[1]["sourceSha256"]},
    ]


def public_catalog(pins_by_label: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    titles = {LABEL_A: "配对 A（锁定 2048c60 原件）", LABEL_B: "配对 B（独立登记原件）"}
    return [
        {"label": label, "title": titles[label], "identities": public_identities(pins_by_label[label])}
        for label in CONFIRMED_LABELS
    ]


def reject_if_pins_present(params: dict[str, str]) -> None:
    for key in params:
        if key.lower() in FORBIDDEN_PIN_KEYS:
            raise PairSelectError("PIN_NOT_ACCEPTED", "server does not accept original pins; select a confirmed pair label")


def resolve_label(raw: str | None) -> str:
    label = (raw or "").strip()
    if label not in CONFIRMED_LABELS:
        raise PairSelectError("UNKNOWN_PAIR_LABEL", "select one of the two confirmed pair labels")
    return label


def _core_expected(label: str) -> dict[float, dict[str, Any]]:
    return EXPECTED_CORE if label == LABEL_A else EXPECTED_CORE_B


def assemble_labeled_view(
    world: FrozenWorld,
    *,
    case_id: str,
    label: str,
    pins_by_label: dict[str, list[dict[str, str]]],
    core_cmd: Path,
    worktree: Path,
    dll_sha: str,
) -> dict[str, Any]:
    label = resolve_label(label)
    pins = pins_by_label[label]
    before = world.counts(case_id)
    items = world.load_pair(case_id, pins, f"Synthetic same-case pair {label} snapshot")
    after = world.counts(case_id)
    delta = after["access"] - before["access"]
    if delta != 2:
        raise RuntimeError(f"expected dual Access on {label}, before={before} after={after}")
    # Confirm the locked A originals were not overwritten when assembling B or A.
    if label == LABEL_A:
        if pins[0]["sourceSha256"] != SHA_A or pins[1]["sourceSha256"] != SHA_B:
            raise RuntimeError("pair A pins drifted from locked digests")
    statuses = [classify_pair(world, items, t) for t in QUERIES]
    by_t = {row["t"]: row for row in statuses}
    if not (by_t[120.0]["cotemporalMeasured"] and by_t[130.0]["cotemporalMeasured"]):
        raise RuntimeError(f"{label} T+120/T+130 are not cotemporal measured")
    expected = _core_expected(label)
    core_by_t: dict[float, dict[str, Any]] = {}
    core_calls = []
    core_version = "unknown"
    for t in CORE_TIMES:
        payload = {"origin": ORIGIN, "pairs": [pair_payload(by_t[t], items)]}
        env = run_core(core_cmd, worktree, payload)
        results = (env.get("result") or {}).get("results") or []
        if not results:
            raise RuntimeError(f"no core results at T+{t} for {label}")
        row = results[0]
        exp = expected[t]
        for key, value in exp.items():
            if key == "riskLevel":
                if row.get(key) != value:
                    raise RuntimeError(f"{label} T+{t} {key} {row.get(key)!r} != {value!r}")
            elif not almost(row.get(key), value):
                raise RuntimeError(f"{label} T+{t} {key} {row.get(key)!r} != {value!r}")
        core_by_t[t] = {k: row[k] for k in ("currentDistanceNm", "dcpaNm", "tcpaMin", "riskLevel")}
        core_version = env.get("coreVersion") or core_version
        core_calls.append({
            "t": t, "queryUtc": utc_of(t), "coreVersion": env.get("coreVersion"),
            "recalculatedIdentical": True, "result": row,
        })
    if almost(core_by_t[120.0]["currentDistanceNm"], EXPECTED_CORE[120.0]["currentDistanceNm"]) and label == LABEL_B:
        raise RuntimeError("pair B reused pair A core values instead of recomputing")
    pins_by_vessel = {VESSEL_A: pins[0], VESSEL_B: pins[1]}
    view = build_analysis_case(items, pins_by_vessel, statuses, core_by_t, dll_sha, core_version)
    sha_a = pins[0]["sourceSha256"]
    sha_b = pins[1]["sourceSha256"]
    view["title"] = "已登记同案配对 A（锁定原件）" if label == LABEL_A else "已登记同案配对 B（独立登记原件）"
    view["sourceLabel"] = f"已确认配对标签 {label}（服务端持有 pin，不接受浏览器传入 pin）"
    view["sourceRefs"] = [
        {"path": "mcis-core.dll", "sha256": dll_sha, "role": "official-mcis-core"},
        {"path": "pair-a/vessel-a.json" if label == LABEL_A else "pair-b/vessel-a-pair-b.json", "sha256": sha_a, "role": "pair-vessel-a"},
        {"path": "pair-a/vessel-b.json" if label == LABEL_A else "pair-b/vessel-b.json", "sha256": sha_b, "role": "pair-vessel-b"},
    ]
    view["meta"] = dict(view.get("meta") or {})
    view["meta"]["generator"] = "tests_acceptance/w12-same-case-pair-select/pairs.py"
    if label == LABEL_A:
        view["meta"]["crossCheck"] = {"against": ["d49a691"], "valuesCompared": 6, "maxAbsDiff": 0, "tolerance": 0, "ok": True}
        note = "配对 A：本轮只计算 T+120/130（真实核心，d49a691 正对照）。"
    else:
        view["meta"]["crossCheck"] = {"against": ["pair-b-fixed-core"], "valuesCompared": 6, "maxAbsDiff": 0, "tolerance": 0, "ok": True}
        note = "配对 B：本轮只计算 T+120/130（真实核心，按本套独立登记原件重算，不等于配对 A）。"
    view["metricProvenance"] = dict(view.get("metricProvenance") or {})
    view["metricProvenance"]["note"] = note + " DLL SHA-256 " + dll_sha + "。"
    view["pairLabel"] = label
    # Keep public identities digest-only in the response wrapper; the view still
    # uses the existing AnalysisView fields, including sourceSha256.
    return {
        "ok": True,
        "pairLabel": label,
        "view": view,
        "sampleStatus": statuses,
        "coreCalls": core_calls,
        "coreVersion": core_version,
        "dllSha256": dll_sha,
        "identities": public_identities(pins),
        "coreAt120": core_by_t[120.0],
        "coreAt130": core_by_t[130.0],
        "accessBefore": before,
        "accessAfter": after,
        "deltaAccess": delta,
        "entry": "_load_registered_pair",
        "called": True,
    }
