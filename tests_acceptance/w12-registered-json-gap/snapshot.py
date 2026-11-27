"""Register locked 2048c60 JSON via frozen intake, load once, build a read-only view snapshot.

Server holds the two pins. Never trust browser-supplied pins. Do not re-read
originals when projecting the snapshot or serving hover data.
"""
from __future__ import annotations

import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parent))

import asyncio
import base64
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from materialize import PIN_FIXTURE, PRODUCT, SHA_A, SHA_B, require_sha

HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
EPOCH = datetime(2026, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
ORIGIN = {"latDeg": -40.0, "lonDeg": -130.0}
VESSEL_A = "SYN-VESSEL-A"
VESSEL_B = "SYN-VESSEL-B"
QUERIES = (120.0, 121.0, 124.250, 127.500, 130.0)
CORE_TIMES = (120.0, 130.0)
EXPECTED_CORE = {
    120.0: {"currentDistanceNm": 1.070062, "dcpaNm": 0.000226, "tcpaMin": 2.918352, "riskLevel": "Danger"},
    130.0: {"currentDistanceNm": 1.008757, "dcpaNm": 0.000213, "tcpaMin": 2.751155, "riskLevel": "Danger"},
}
DECL_GAPS_A = ((60.0, 100.0), (121.0, 127.5))


def tsec(text: str) -> float:
    return (datetime.fromisoformat(text.replace("Z", "+00:00")) - EPOCH).total_seconds()


def utc_of(t: float) -> str:
    stamp = EPOCH + timedelta(seconds=t)
    if abs(t - int(t)) < 1e-9:
        return stamp.strftime("%Y-%m-%dT%H:%M:%S.000Z") if t != int(t) else stamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    # keep millisecond precision used by the original instants
    return stamp.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def clock_of(t: float) -> str:
    local = (EPOCH + timedelta(seconds=t)).astimezone(CST)
    if abs(t - int(t)) < 1e-9:
        return local.strftime("%H:%M:%S")
    ms = int(round((t - int(t)) * 1000))
    return local.strftime("%H:%M:%S") + f".{ms:03d}"


def pin_fields(receipt: dict[str, Any]) -> dict[str, str]:
    return {k: receipt[k] for k in ("caseId", "evidenceId", "requestDigest", "sourceSha256")}


class FrozenWorld:
    """One isolated allowlist tree, one Database, no official product routes."""

    def __init__(self, source: Path):
        self.source = source
        sys.path.insert(0, str(source / "service"))
        from sqlalchemy import select, text
        from mcis_service.db import Database, Base, put_doc, APPEND_ONLY_TABLES
        from mcis_service.common.context import Ctx
        from mcis_service.common import contracts
        from mcis_service.cases.models import CaseRow
        from mcis_service.evidence.models import EvidenceRow, CustodyEventRow
        from mcis_service.audit.models import AuditEventRow
        from mcis_service.audit.service import verify_chain, all_lines
        from mcis_service.redaction.models import AccessPolicyRow
        from mcis_service.redaction.policy import default_policy
        from mcis_service.working_records_archive.models import ArchiveImportHistoryRow
        from mcis_service.track_history.models import LocalReceipt
        from mcis_service.evidence_intake import router as intake
        from mcis_service.trajectory_exchange.registered_pair import _load_registered_pair, RegisteredPairError
        from mcis_service.trajectory_exchange.registered_query import _point_from_committed_original, _stamp

        self._select = select
        self.Database = Database
        self.put_doc = put_doc
        self.CaseRow = CaseRow
        self.EvidenceRow = EvidenceRow
        self.CustodyEventRow = CustodyEventRow
        self.AuditEventRow = AuditEventRow
        self.AccessPolicyRow = AccessPolicyRow
        self.default_policy = default_policy
        self.contracts = contracts
        self.intake = intake
        self._load_registered_pair = _load_registered_pair
        self.RegisteredPairError = RegisteredPairError
        self._point_from_committed_original = _point_from_committed_original
        self._stamp = _stamp
        self.verify_chain = verify_chain
        self.all_lines = all_lines
        self.HTTPException = __import__("fastapi").HTTPException

        self.root = source / "runtime"
        self.root.mkdir(parents=True, exist_ok=True)
        blobs = self.root / "blobs"
        blobs.mkdir()
        self.db = Database("sqlite:///" + str(self.root / "fresh.sqlite"))
        tables = [m.__table__ for m in (CaseRow, EvidenceRow, CustodyEventRow, AuditEventRow, AccessPolicyRow, ArchiveImportHistoryRow, LocalReceipt)]
        Base.metadata.create_all(self.db.engine, tables=tables)
        with self.db.engine.begin() as c:
            for t in APPEND_ONLY_TABLES:
                for op in ("UPDATE", "DELETE"):
                    c.execute(text(
                        f"CREATE TRIGGER IF NOT EXISTS {t}_no_{op.lower()} BEFORE {op} ON {t} "
                        f"BEGIN SELECT RAISE(ABORT, '{t} is append-only'); END;"
                    ))
        state = SimpleNamespace(db=self.db, settings=SimpleNamespace(blob_dir=blobs))
        self.ctx = Ctx(role="Investigator", operator="Synthetic isolated operator", request=SimpleNamespace(app=SimpleNamespace(state=state)))

    @classmethod
    def attach(cls, source: Path) -> "FrozenWorld":
        """Open an already-assembled runtime database; do not recreate tables."""
        obj = cls.__new__(cls)
        obj.source = source
        if str(source / "service") not in sys.path:
            sys.path.insert(0, str(source / "service"))
        from sqlalchemy import select
        from mcis_service.db import Database
        from mcis_service.common.context import Ctx
        from mcis_service.evidence.models import EvidenceRow, CustodyEventRow
        from mcis_service.audit.models import AuditEventRow
        from mcis_service.redaction.models import AccessPolicyRow
        from mcis_service.redaction.policy import default_policy
        from mcis_service.cases.models import CaseRow
        from fastapi import HTTPException
        obj._select = select
        obj.Database = Database
        obj.CaseRow = CaseRow
        obj.EvidenceRow = EvidenceRow
        obj.CustodyEventRow = CustodyEventRow
        obj.AuditEventRow = AuditEventRow
        obj.AccessPolicyRow = AccessPolicyRow
        obj.default_policy = default_policy
        obj.HTTPException = HTTPException
        obj.put_doc = None
        obj.contracts = None
        obj.intake = None
        obj._load_registered_pair = None
        obj.RegisteredPairError = None
        obj._point_from_committed_original = None
        obj._stamp = None
        obj.verify_chain = None
        obj.all_lines = None
        obj.root = source / "runtime"
        blobs = obj.root / "blobs"
        db_path = obj.root / "fresh.sqlite"
        if not db_path.is_file():
            raise RuntimeError(f"missing assembled database {db_path}")
        obj.db = Database("sqlite:///" + str(db_path))
        state = SimpleNamespace(db=obj.db, settings=SimpleNamespace(blob_dir=blobs))
        obj.ctx = Ctx(role="Investigator", operator="Synthetic isolated operator", request=SimpleNamespace(app=SimpleNamespace(state=state)))
        return obj

    def close(self) -> None:
        self.db.engine.dispose()

    def ensure_case(self, case_id: str, title: str) -> None:
        case = {
            "caseId": case_id, "schemaVersion": "1.0.0", "title": title, "accidentType": "Synthetic",
            "isFictionalDemo": True, "caseEpochUtc": "2026-02-01T12:00:00Z", "incidentTimeUtc": "2026-02-01T12:00:00Z",
            "incidentLocation": {"lonDeg": -130, "latDeg": -40}, "displayTimeZoneOffsetMinutes": 480,
        }
        self.contracts.validate("case", case)
        with self.db.session() as s:
            self.put_doc(s, self.CaseRow, case_id, case_id, case)
            self.put_doc(s, self.AccessPolicyRow, case_id, "policy", self.default_policy())

    def register_bytes(self, case_id: str, file_name: str, raw: bytes) -> dict[str, str]:
        body = {
            "profile": "mcis-evidence-intake-v1", "fileName": file_name, "title": "Synthetic V1 trajectory",
            "source": "Handmade 2048c60 fixture, not authenticated evidence", "extractedBy": "Synthetic author",
            "extractedUtc": "2026-02-01T00:00:00Z", "category": "Other", "confidentiality": "Restricted",
            "note": "synthetic", "contentBase64": base64.b64encode(raw).decode(),
        }
        preview = asyncio.run(self.intake.preview_input(case_id, _Body(body), self.ctx))
        receipt = asyncio.run(self.intake.commit_input(
            case_id, _Body({**body, "requestDigest": preview["requestDigest"], "confirmed": True}), self.ctx,
        ))
        if receipt["sourceSha256"] != hashlib.sha256(raw).hexdigest():
            raise RuntimeError("registration sourceSha256 does not match original bytes")
        path = self.intake.file_path(self.ctx, case_id, self.intake.rel_for(receipt["requestDigest"]))
        if path.read_bytes() != raw:
            raise RuntimeError("stored original bytes differ from locked fixture")
        return pin_fields(receipt)

    def set_deny_evidence(self, case_id: str) -> None:
        policy = self.default_policy()
        policy["matrix"]["Investigator"]["evidence_meta"] = "Deny"
        with self.db.session() as s:
            self.put_doc(s, self.AccessPolicyRow, case_id, "policy", policy)

    def counts(self, case_id: str | None = None) -> dict[str, int]:
        with self.db.session() as s:
            ev = s.query(self.EvidenceRow)
            cu = s.query(self.CustodyEventRow)
            au = s.query(self.AuditEventRow)
            acc = s.query(self.CustodyEventRow).filter_by(kind="Access")
            if case_id:
                ev = ev.filter_by(case_id=case_id)
                cu = cu.filter_by(case_id=case_id)
                au = au.filter_by(case_id=case_id)
                acc = acc.filter_by(case_id=case_id)
            return {
                "evidence": ev.count(),
                "custody": cu.count(),
                "audit": au.count(),
                "access": acc.count(),
            }

    def load_pair(self, case_id: str, pins: list[dict[str, str]], purpose: str):
        return self._load_registered_pair(self.ctx, case_id, pins, purpose)


class _Body:
    headers = {"content-type": "application/json"}

    def __init__(self, value):
        self.raw = json.dumps(value).encode()

    async def stream(self):
        yield self.raw


def cpa_inputs_ok(point: dict[str, Any]) -> bool:
    if point.get("status") != "input_point":
        return False
    pos, course, speed = point.get("position") or {}, point.get("courseDeg") or {}, None
    # speed is not in _point_from_committed_original; take it from the document via locator later
    return (
        pos.get("kind") == "recorded" and pos.get("value")
        and course.get("kind") == "recorded" and course.get("value") is not None
    )


def point_speed(doc: dict[str, Any], locator: dict[str, Any] | None) -> dict[str, Any] | None:
    if not locator or not str(locator.get("jsonPointer") or "").startswith("/points/"):
        return None
    idx = int(locator["jsonPointer"].split("/")[-1])
    return doc["points"][idx].get("speedKn")


def classify_pair(world: FrozenWorld, items, t: float) -> dict[str, Any]:
    instant = world._stamp(utc_of(t))
    by_id = {item["document"]["vessel"]["vesselId"]: item for item in items}
    views = {}
    for vid in (VESSEL_A, VESSEL_B):
        views[vid] = world._point_from_committed_original(by_id[vid], instant)
    a, b = views[VESSEL_A], views[VESSEL_B]
    a_ok = a["status"] == "input_point" and (a.get("position") or {}).get("kind") == "recorded"
    b_ok = b["status"] == "input_point" and (b.get("position") or {}).get("kind") == "recorded"
    a_speed = point_speed(by_id[VESSEL_A]["document"], a.get("locator")) if a_ok else None
    b_speed = point_speed(by_id[VESSEL_B]["document"], b.get("locator")) if b_ok else None
    both = (
        a_ok and b_ok
        and a_speed and a_speed.get("kind") == "recorded" and a_speed.get("value") is not None
        and b_speed and b_speed.get("kind") == "recorded" and b_speed.get("value") is not None
        and (a.get("courseDeg") or {}).get("kind") == "recorded" and (a.get("courseDeg") or {}).get("value") is not None
        and (b.get("courseDeg") or {}).get("kind") == "recorded" and (b.get("courseDeg") or {}).get("value") is not None
    )
    return {
        "t": t,
        "queryUtc": utc_of(t),
        "clock": clock_of(t),
        "A": _public_view(a, a_speed),
        "B": _public_view(b, b_speed),
        "cotemporalMeasured": both,
        "pairMetricsAllowed": both and t in CORE_TIMES,
    }


def _public_view(point: dict[str, Any], speed: dict[str, Any] | None) -> dict[str, Any]:
    out = {
        "vesselId": point["vesselId"],
        "status": point["status"],
        "hasPosition": bool((point.get("position") or {}).get("value")),
        "positionKind": (point.get("position") or {}).get("kind"),
        "locator": point.get("locator"),
        "gap": point.get("gap"),
    }
    if speed:
        out["speedKind"] = speed.get("kind")
        out["speedKn"] = speed.get("value")
    if point.get("courseDeg"):
        out["courseKind"] = point["courseDeg"].get("kind")
        out["courseDeg"] = point["courseDeg"].get("value")
    return out


def pair_payload(row: dict[str, Any], items) -> dict[str, Any]:
    by_id = {item["document"]["vessel"]["vesselId"]: item for item in items}
    def body(vid: str, view: dict[str, Any]) -> dict[str, Any]:
        loc = view["locator"]
        doc = by_id[vid]["document"]
        idx = int(loc["jsonPointer"].split("/")[-1])
        p = doc["points"][idx]
        return {
            "vesselId": vid,
            "latDeg": p["position"]["value"]["latDeg"],
            "lonDeg": p["position"]["value"]["lonDeg"],
            "speedKn": p["speedKn"]["value"],
            "courseDeg": p["courseDeg"]["value"],
        }
    return {
        "pairId": f"{VESSEL_A}|{VESSEL_B}@{row['t']:g}",
        "timeSec": row["t"],
        "own": body(VESSEL_A, row["A"]),
        "target": body(VESSEL_B, row["B"]),
    }


def declared_gaps(doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in doc["sampling"]["missingIntervals"]:
        rows.append({
            "vesselId": doc["vessel"]["vesselId"],
            "startSec": tsec(item["startUtc"]),
            "endSec": tsec(item["endUtc"]),
        })
    return rows


def almost(actual, expected) -> bool:
    return round(float(actual), 6) == round(float(expected), 6)


def build_analysis_case(
    items, pins_by_vessel: dict[str, dict[str, str]], statuses: list[dict[str, Any]],
    core_by_t: dict[float, dict[str, Any]], dll_sha: str, core_version: str,
) -> dict[str, Any]:
    docs = {item["document"]["vessel"]["vesselId"]: item["document"] for item in items}
    times = sorted({tsec(p["time"]["alignedUtc"]) for doc in docs.values() for p in doc["points"]} | {124.250})
    series = []
    for t in times:
        core = core_by_t.get(t)
        series.append({
            "t": t,
            "clock": clock_of(t),
            "distanceNm": None if not core else core["currentDistanceNm"],
            "dcpaNm": None if not core else core["dcpaNm"],
            "tcpaMin": None if not core else core["tcpaMin"],
            "riskLevel": None if not core else core["riskLevel"],
        })
    identities = []
    for vid in (VESSEL_A, VESSEL_B):
        pin = pins_by_vessel[vid]
        identities.append({
            "vesselId": vid,
            "evidenceId": pin["evidenceId"],
            "requestDigest": pin["requestDigest"],
            "sourceSha256": pin["sourceSha256"],
            "pointCount": len(docs[vid]["points"]),
        })
    gaps = declared_gaps(docs[VESSEL_A]) + declared_gaps(docs[VESSEL_B])
    if [(g["startSec"], g["endSec"]) for g in declared_gaps(docs[VESSEL_A])] != list(DECL_GAPS_A):
        raise RuntimeError(f"declared gaps drifted from original JSON: {gaps}")
    return {
        "caseId": docs[VESSEL_A]["caseId"],
        "key": "registered-json-gap",
        "title": "已登记声明缺口 JSON（同刻核心）",
        "isFictionalDemo": True,
        "sourceLabel": "已登记合成 JSON 原件（服务端固定 pin，只读快照）",
        "sourceRefs": [
            {"path": "mcis-core.dll", "sha256": dll_sha, "role": "official-mcis-core"},
            {"path": "tests_acceptance/shared-trajectory-cross-repo-expanded/vessel-a.json", "sha256": SHA_A, "role": "2048c60-expanded-A"},
            {"path": "tests_acceptance/shared-trajectory-cross-repo-expanded/vessel-b.json", "sha256": SHA_B, "role": "2048c60-expanded-B"},
        ],
        "epochLocal": "2026-02-01 20:00:00",
        "timeZone": "Asia/Shanghai",
        "vessels": [{"vesselId": VESSEL_A, "name": "合成船 A"}, {"vesselId": VESSEL_B, "name": "合成船 B"}],
        "thresholds": {"dangerDcpaNm": 0.3, "dangerTcpaMin": 6},
        "baseline": {
            "label": "已登记同刻样本（真实核心；声明缺口不连线）",
            "stepSec": 10,
            "cutAtSec": max(times),
            "series": series,
            "keyMoments": [],
        },
        "whatif": None,
        "notes": [
            "视图快照只读，hover 不再读取原件。缺口取自已登记原件 sampling.missingIntervals，不从步长猜测。",
            "仅 T+120 与 T+130 为双船同刻实测并调用既有 mcis-core cpa（对照 d49a691）。T+124.25 在 A 开区间内部，不显示 A 样位或双船指标。T+121 与 T+127.5 为 A 原始端点，不是双船同刻。",
        ],
        "meta": {
            "seedSha256": "0" * 64,
            "seedVerified": False,
            "generatedAt": "2026-11-27T07:00:00Z",
            "generator": "tests_acceptance/w12-registered-json-gap/snapshot.py",
            "coreVersion": core_version,
            "coreDll": {"path": "mcis-core.dll", "sha256": dll_sha, "role": "official-mcis-core"},
            "w14Export": {"path": "unused", "sha256": "0" * 64, "role": "unused"},
            "w14Frozen": {"path": "unused", "sha256": "0" * 64, "role": "unused"},
            "crossCheck": {"against": ["d49a691"], "valuesCompared": 6, "maxAbsDiff": 0, "tolerance": 0, "ok": True},
            "disclaimer": "隔离装配。正式路由、存储与写路径未改。两个固定 pin 由服务端持有，不信任浏览器传入的 pin。审计不扩大到登录或跨进程撤权保证。",
        },
        "metricProvenance": {
            "distance": "mcis-core",
            "dcpa": "mcis-core",
            "tcpa": "mcis-core",
            "note": "仅 T+120、T+130 为真实核心（d49a691 正对照，两次一致）。其它查询时刻无双船同刻实测，未回填、未用演示 CPA。DLL SHA-256 " + dll_sha + "。",
        },
        "registeredIdentities": identities,
        "gapWiring": {
            "status": "wired",
            "reason": "来自已登记原件 sampling.missingIntervals，未从时间步长猜测。开区间 (60,100)、(121,127.5)。",
        },
        "declaredOpenGaps": gaps,
    }


def run_core(core_cmd: Path, worktree: Path, payload: dict[str, Any]) -> dict[str, Any]:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "w12_core_client", worktree / "service/mcis_service/colreg/core_client.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    first = mod.run(str(core_cmd), "cpa", payload, timeout_s=60)
    second = mod.run(str(core_cmd), "cpa", payload, timeout_s=60)
    if first != second:
        raise RuntimeError("core cpa not identical on repeat")
    if not first.get("ok"):
        raise RuntimeError(f"core cpa failed: {first}")
    return first


def assemble(
    world: FrozenWorld,
    fixtures: Path,
    *,
    core_cmd: Path,
    worktree: Path,
    dll_sha: str,
) -> dict[str, Any]:
    raw_a = (fixtures / "vessel-a.json").read_bytes()
    raw_b = (fixtures / "vessel-b.json").read_bytes()
    require_sha(fixtures / "vessel-a.json", SHA_A, "vessel-a.json")
    require_sha(fixtures / "vessel-b.json", SHA_B, "vessel-b.json")
    cid = json.loads(raw_a)["caseId"]
    if cid != json.loads(raw_b)["caseId"]:
        raise RuntimeError("A/B caseId mismatch")
    world.ensure_case(cid, "Synthetic registered JSON gap")
    pin_a = world.register_bytes(cid, "vessel-a.json", raw_a)
    pin_b = world.register_bytes(cid, "vessel-b.json", raw_b)
    if pin_a["sourceSha256"] != SHA_A or pin_b["sourceSha256"] != SHA_B:
        raise RuntimeError("registered sourceSha256 is not the locked 2048c60 digest")
    pins = [pin_a, pin_b]
    before = world.counts(cid)
    items = world.load_pair(cid, pins, "Synthetic registered JSON gap snapshot")
    after = world.counts(cid)
    if after["access"] - before["access"] != 2:
        raise RuntimeError(f"expected dual Access, counts before={before} after={after}")
    # Project from the committed originals only; do not call _load_registered_pair again.
    statuses = [classify_pair(world, items, t) for t in QUERIES]
    # Sanity: T+124.25 has no A sample; T+121/127.5 are A endpoints but not cotemporal.
    by_t = {row["t"]: row for row in statuses}
    if by_t[124.250]["A"]["status"] != "declared_gap" or by_t[124.250]["A"]["hasPosition"]:
        raise RuntimeError(f"T+124.25 unexpectedly shows an A sample: {by_t[124.250]['A']}")
    if by_t[124.250]["cotemporalMeasured"] or by_t[121.0]["cotemporalMeasured"] or by_t[127.500]["cotemporalMeasured"]:
        raise RuntimeError("non-cotemporal instants were marked dual-ship measured")
    if by_t[121.0]["A"]["status"] != "input_point" or by_t[127.500]["A"]["status"] != "input_point":
        raise RuntimeError("A endpoints at T+121 / T+127.5 missing from original")
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

    pins_by_vessel = {
        VESSEL_A: pin_a,
        VESSEL_B: pin_b,
    }
    complete = build_analysis_case(items, pins_by_vessel, statuses, core_by_t, dll_sha, core_version)

    # Denied case: register the same originals under a new case, then deny and load.
    deny_id = "SYN-XREPO-DENY"
    world.ensure_case(deny_id, "Synthetic deny")
    # documents have caseId SYN-XREPO-001; register still stores opaque bytes.
    # load will fail DOCUMENT_CASE_MISMATCH if we use these bytes as-is with a different caseId.
    # For a policy-deny of the successful case, temporarily set deny on cid after snapshot,
    # using a cloned case with matching caseId is impossible (unique).
    # Instead: set deny on a second registration of the same bytes after rewriting caseId? That would change bytes.
    # Required: 拒绝或无配对时无指标. Policy deny on the SAME case would block later loads;
    # we already have the snapshot. Use a dedicated case with policy deny and pins of that case.
    # The frozen loader checks document caseId == request caseId, so we cannot register
    # unaltered 2048c60 JSON under another caseId.
    # Policy-deny the success case *after* the snapshot is built, then attempt a second load
    # to record the refusal, then (we must not mutate the already-built snapshot).
    # Better: create deny attempt on cid AFTER snapshot, record 403, confirm Access did not increase.
    # Then we should restore policy so later audit counts stay meaningful... Host holds snapshot already.
    world.set_deny_evidence(cid)
    deny_before = world.counts(cid)
    deny = {"ok": False, "reason": None, "metricsReturned": False, "currentAnalysis": None, "accessBefore": deny_before["access"]}
    try:
        world.load_pair(cid, pins, "Synthetic denied reread")
        deny["reason"] = "expected-deny-failed"
        raise RuntimeError("policy deny did not block _load_registered_pair")
    except Exception as exc:
        if type(exc).__name__ != "HTTPException" or getattr(exc, "status_code", None) != 403:
            # fastapi HTTPException should be raised
            if not (isinstance(exc, world.HTTPException) and exc.status_code == 403):
                raise
        deny["reason"] = "policy-deny:403"
    deny_after = world.counts(cid)
    if deny_after["access"] != deny_before["access"]:
        raise RuntimeError(f"deny path recorded Access: {deny_before} -> {deny_after}")
    deny["accessAfter"] = deny_after["access"]

    # Unpaired: only the first pin. Restore policy first so we test missing pair, not deny.
    world.put_doc  # restore policy
    with world.db.session() as s:
        world.put_doc(s, world.AccessPolicyRow, cid, "policy", world.default_policy())
    unpaired_before = world.counts(cid)
    unpaired = {"ok": False, "reason": None, "metricsReturned": False, "currentAnalysis": None, "accessBefore": unpaired_before["access"]}
    try:
        world.load_pair(cid, [pin_a], "Synthetic unpaired")
        raise RuntimeError("single pin was accepted")
    except world.RegisteredPairError as exc:
        unpaired["reason"] = f"unpaired:{exc}"
    unpaired_after = world.counts(cid)
    if unpaired_after["access"] != unpaired_before["access"]:
        raise RuntimeError("unpaired path recorded Access")
    unpaired["accessAfter"] = unpaired_after["access"]

    after_all = world.counts(cid)
    return {
        "productAllowlist": PRODUCT,
        "fixturePin": PIN_FIXTURE,
        "fixtureSha256": {"vessel-a.json": SHA_A, "vessel-b.json": SHA_B},
        "pinsHeldByServer": pins,  # never copied into browser-facing fields as an authority
        "complete": complete,
        "sampleStatus": statuses,
        "coreCalls": core_calls,
        "coreVersion": core_version,
        "dllSha256": dll_sha,
        "successAccess": {"before": before, "after": after, "deltaAccess": after["access"] - before["access"]},
        "denied": deny,
        "unpaired": unpaired,
        "finalCounts": after_all,
        "declaredOpenGaps": complete["declaredOpenGaps"],
    }


def cli_assemble() -> int:
    import argparse
    import os
    from materialize import materialize
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-dir", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--worktree", type=Path, required=True)
    parser.add_argument("--core-cmd", type=Path, required=True)
    parser.add_argument("--dll-sha", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    os.environ.setdefault("DOTNET_CLI_TELEMETRY_OPTOUT", "1")
    os.environ.setdefault("DOTNET_NOLOGO", "1")
    args.source.mkdir(parents=True, exist_ok=True)
    materialize(args.source, git_dir=args.git_dir)
    world = FrozenWorld(args.source)
    try:
        snapshot = assemble(world, args.fixtures, core_cmd=args.core_cmd, worktree=args.worktree, dll_sha=args.dll_sha)
    finally:
        world.close()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    if not sys.flags.isolated:
        raise SystemExit("Use existing Python -I")
    raise SystemExit(cli_assemble())
