"""Reuse 8266aba's verified same-transaction capture and exact-sample core call.

Product code is imported, not copied. Does not call state_at or GET /cpa.
Does not change official storage, write paths, or contracts.
"""
from __future__ import annotations

import base64
import json
from typing import Any
from urllib import error, request

CASE_OK = "SYN-W12-FR-AB"
CASE_MISS = "SYN-W12-FR-INCOMPLETE"
OWN, TARGET = "SYN-OWN", "SYN-TGT"
EPOCH = "2026-01-01T00:00:00Z"
ORIGIN = {"latDeg": 31.0, "lonDeg": 121.0}
OPERATOR = "SyntheticPilot"
ROLE = "Investigator"

OWN_ROWS = [
    ("2026-01-01T00:00:00Z", 31.000, 121.000, 10.0, 0.0),
    ("2026-01-01T00:00:10Z", 31.010, 121.000, 10.0, 0.0),
    ("2026-01-01T00:00:20Z", 31.020, 121.000, 10.0, 0.0),
    ("2026-01-01T00:00:30Z", 31.030, 121.000, 10.0, 0.0),
]
TGT_ROWS = [
    ("2026-01-01T00:00:10Z", 31.010, 121.050, 10.0, 270.0),
    ("2026-01-01T00:00:20Z", 31.010, 121.040, 10.0, 270.0),
    ("2026-01-01T00:00:40Z", 31.010, 121.030, 10.0, 270.0),
]
COMMON_TIMES = (10.0, 20.0)
OUTSIDE_TIMES = (0.0, 15.0, 30.0, 40.0)
CSV_HEADER = "utc,latDeg,lonDeg,sogKn,sogStatus,cogDeg,cogStatus\n"
GAP_UNWIRED_REASON = (
    "登记原件为 mcis-utc-v1 合成 CSV，没有授权的显式缺口元数据；"
    "保持未接，不从时间步长猜测，不新造契约。"
)


def csv_bytes(rows: list[tuple]) -> bytes:
    body = CSV_HEADER + "".join(
        f"{utc},{lat},{lon},{sog},reported,{cog},reported\n" for utc, lat, lon, sog, cog in rows
    )
    return body.encode("utf-8")


def import_body(vessel_id: str, raw: bytes) -> dict[str, Any]:
    return {
        "profile": "mcis-utc-v1",
        "vesselId": vessel_id,
        "fileName": f"{vessel_id}.csv",
        "source": "synthetic W12 first-registered wiring; not a real case",
        "timeBasis": "declared synthetic UTC Z timestamps",
        "contentBase64": base64.b64encode(raw).decode("ascii"),
    }


def case_body(case_id: str) -> dict[str, Any]:
    return {
        "caseId": case_id,
        "schemaVersion": "1.0.0",
        "title": "Synthetic first-registered wiring",
        "accidentType": "Collision",
        "incidentTimeUtc": EPOCH,
        "caseEpochUtc": EPOCH,
        "displayTimeZoneOffsetMinutes": 0,
        "incidentLocation": {**ORIGIN, "heightM": 0},
        "isFictionalDemo": True,
    }


class Http:
    def __init__(self, base: str):
        self.base = base.rstrip("/")

    def call(self, path: str, body: Any | None = None, method: str | None = None) -> tuple[int, Any]:
        headers = {"X-MCIS-Role": ROLE, "X-MCIS-Operator": OPERATOR}
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=30) as resp:
                raw, status = resp.read(), resp.status
        except error.HTTPError as exc:
            raw, status = exc.read(), exc.code
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeError):
            parsed = raw.decode("utf-8", "replace")
        return status, parsed


def exact_times(points: list[dict[str, Any]]) -> dict[float, dict[str, Any]]:
    out: dict[float, dict[str, Any]] = {}
    for p in points:
        t = float(p["timeSec"])
        if t in out:
            raise ValueError(f"duplicate sample time {t}")
        out[t] = p
    return out


def pair_at(own_id: str, tgt_id: str, t: float, a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    def st(vid: str, p: dict[str, Any]) -> dict[str, Any]:
        return {
            "vesselId": vid,
            "latDeg": p["latDeg"],
            "lonDeg": p["lonDeg"],
            "speedKn": p["sogKn"],
            "courseDeg": p["cogDeg"],
        }

    return {"pairId": f"{own_id}|{tgt_id}@{t:g}", "timeSec": t, "own": st(own_id, a), "target": st(tgt_id, b)}


def capture_in_one_transaction(app, case_id: str, expected: list[str], digests: dict[str, str]) -> dict[str, Any]:
    """Load verified receipts and point arrays in one reserved SQLite transaction."""
    from mcis_service.common.context import Ctx
    from mcis_service.cases.service import track_points
    from mcis_service.db import WRITE_LOCK
    from mcis_service.reports.access import begin
    from mcis_service.tracks_import.router import authorize, load_receipt

    class _Req:
        def __init__(self, application):
            self.app = application

    ctx = Ctx(role=ROLE, operator=OPERATOR, request=_Req(app))
    result: dict[str, Any] = {
        "ok": False,
        "reason": None,
        "identities": {},
        "points": {},
        "commonTimes": [],
        "transaction": "WRITE_LOCK+BEGIN IMMEDIATE, read only",
    }
    with WRITE_LOCK, ctx.db.session() as session:
        begin(session)
        authorize(ctx, session, case_id)
        for vid in expected:
            digest = digests.get(vid)
            if not digest:
                result["reason"] = f"missing-receipt:{vid}"
                return result
            saved = load_receipt(ctx, session, case_id, digest)
            if saved is None:
                result["reason"] = f"receipt-not-found:{vid}"
                return result
            receipt = dict(saved[0])
            if receipt.get("vesselId") != vid or receipt.get("caseId") != case_id:
                result["reason"] = f"identity-mismatch:{vid}"
                return result
            pts = [dict(p) for p in track_points(session, case_id, vid)]
            if len(pts) != receipt.get("pointCount"):
                result["reason"] = f"point-count-mismatch:{vid}"
                return result
            if not pts:
                result["reason"] = f"no-points:{vid}"
                return result
            result["identities"][vid] = {
                "caseId": receipt["caseId"],
                "vesselId": receipt["vesselId"],
                "previewDigest": receipt["previewDigest"],
                "sourceSha256": receipt["sourceSha256"],
                "reportSha256": receipt["reportSha256"],
                "pointCount": receipt["pointCount"],
            }
            result["points"][vid] = pts
        own_map = exact_times(result["points"][expected[0]])
        tgt_map = exact_times(result["points"][expected[1]])
        result["commonTimes"] = sorted(set(own_map) & set(tgt_map))
        result["ok"] = True
        return result


def metrics_for_common_samples(identities: dict, points: dict, core_run, core_cmd: str, times: list[float]) -> dict[str, Any]:
    own_map = exact_times(points[OWN])
    tgt_map = exact_times(points[TARGET])
    present, missing = [], []
    for t in times:
        (present if t in own_map and t in tgt_map else missing).append(t)
    payload = {
        "origin": ORIGIN,
        "pairs": [pair_at(OWN, TARGET, t, own_map[t], tgt_map[t]) for t in present],
    }
    if not payload["pairs"]:
        return {
            "metrics": None,
            "reason": "no-exact-common-samples",
            "requestedTimes": times,
            "missingTimes": missing,
            "identities": identities,
        }
    first = core_run(core_cmd, "cpa", payload, timeout_s=60)
    second = core_run(core_cmd, "cpa", payload, timeout_s=60)
    return {
        "metrics": first.get("result"),
        "coreVersion": first.get("coreVersion"),
        "recalculatedIdentical": first == second,
        "requestedTimes": times,
        "missingTimes": missing,
        "identities": identities,
        "payloadPairs": payload["pairs"],
        "rawFirst": first,
        "rawSecond": second,
    }


def create_and_import(http: Http, case_id: str, vessels: list[tuple[str, bytes]]) -> dict[str, str]:
    status, body = http.call("/cases", case_body(case_id), method="POST")
    if status != 201:
        raise RuntimeError(f"create case {case_id} failed: {status} {body}")
    for vid, _raw in vessels:
        status, body = http.call(
            f"/cases/{case_id}/vessels",
            {"vesselId": vid, "caseId": case_id, "name": f"Synthetic {vid}"},
            method="POST",
        )
        if status != 201:
            raise RuntimeError(f"create vessel {vid} failed: {status} {body}")
    digests: dict[str, str] = {}
    for vid, raw in vessels:
        payload = import_body(vid, raw)
        status, preview = http.call(f"/cases/{case_id}/track-imports:preview", payload)
        if status != 200 or not preview.get("canCommit"):
            raise RuntimeError(f"preview {vid} failed: {status} {preview}")
        status, commit = http.call(
            f"/cases/{case_id}/track-imports:commit",
            {**payload, "confirmed": True, "previewDigest": preview["previewDigest"]},
        )
        if status != 200 or commit.get("replayed") is not False:
            raise RuntimeError(f"commit {vid} failed: {status} {commit}")
        if commit.get("vesselId") != vid or commit.get("previewDigest") != preview["previewDigest"]:
            raise RuntimeError(f"commit identity mismatch {vid}: {commit}")
        digests[vid] = commit["previewDigest"]
    return digests
