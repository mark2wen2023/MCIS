"""Isolated loopback host: assemble the read-only snapshot inside the view request.

127.0.0.1 only. Synthetic test role contexts are not real identity authentication.
One response carries only that role's result; pins stay on the server.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIBLING = HERE.parent / "w12-registered-json-gap"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SIBLING))

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from snapshot import FrozenWorld
from view import assemble_authorized_view, register_locked_pair

# Synthetic test-server role context names. Not real authentication.
ROLE_HEADER = "x-w12-synthetic-role-context"
ROLE_AUTHORIZED = "synthetic-authorized-reader"
ROLE_DENIED = "synthetic-denied-reader"
ROLE_KIND = "synthetic-test-server-role"

STATE: dict = {}
REQUEST_LOG: list[dict] = []


def _role_of(request: Request) -> str:
    return (request.headers.get(ROLE_HEADER) or "").strip()


def _public_authorized(bundle: dict) -> dict:
    view = bundle["view"]
    return {
        "ok": True,
        "roleContext": ROLE_AUTHORIZED,
        "roleContextKind": ROLE_KIND,
        "roleContextNote": "合成测试服务端角色上下文，不是真实身份认证",
        "view": view,
        "sampleStatus": bundle["sampleStatus"],
        "coreVersion": bundle["coreVersion"],
        "dllSha256": bundle["dllSha256"],
        "declaredOpenGaps": bundle["declaredOpenGaps"],
        "accessBefore": bundle["accessBefore"],
        "accessAfter": bundle["accessAfter"],
        "deltaAccess": bundle["deltaAccess"],
    }


def _denied_body(*, reason: str, before: dict, after: dict) -> dict:
    return {
        "ok": False,
        "reason": reason,
        "roleContext": ROLE_DENIED if reason != "missing-synthetic-role-context" else "",
        "roleContextKind": ROLE_KIND,
        "roleContextNote": "合成测试服务端角色上下文，不是真实身份认证",
        "metricsReturned": False,
        "currentAnalysis": None,
        "view": None,
        "registeredIdentities": None,
        "accessBefore": before,
        "accessAfter": after,
        "deltaAccess": after["access"] - before["access"],
    }


def _safe_log_payload(payload: dict) -> dict:
    """Keep raw request results without server pins or original JSON bodies."""
    out = {k: payload[k] for k in payload if k != "view"}
    if payload.get("ok") and isinstance(payload.get("view"), dict):
        view = payload["view"]
        out["viewSummary"] = {
            "caseId": view.get("caseId"),
            "title": view.get("title"),
            "identityCount": len(view.get("registeredIdentities") or []),
            "hasMetrics": bool(view.get("baseline")),
        }
    return out


def create_app(assembly: Path) -> FastAPI:
    app = FastAPI()

    @app.get("/assembly/api/view")
    def request_time_view(request: Request):
        world = STATE["world"]
        cid = STATE["case_id"]
        role = _role_of(request)
        before = world.counts(cid)
        if role == ROLE_AUTHORIZED:
            bundle = assemble_authorized_view(
                world,
                case_id=cid,
                pins=STATE["pins"],
                core_cmd=STATE["core_cmd"],
                worktree=STATE["worktree"],
                dll_sha=STATE["dll_sha"],
            )
            body = _public_authorized(bundle)
            status = 200
        elif role == ROLE_DENIED:
            after = world.counts(cid)
            if after["access"] != before["access"]:
                raise RuntimeError("denied path must not increment Access")
            body = _denied_body(reason="policy-deny:403", before=before, after=after)
            status = 403
        else:
            after = world.counts(cid)
            body = _denied_body(reason="missing-synthetic-role-context", before=before, after=after)
            # still a business reject, no snapshot
            body["roleContext"] = role
            status = 403
        record = {
            "path": "/assembly/api/view",
            "method": "GET",
            "status": status,
            "roleHeader": role,
            "accessBefore": body["accessBefore"],
            "accessAfter": body["accessAfter"],
            "deltaAccess": body["deltaAccess"],
            "ok": body["ok"],
            "reason": body.get("reason"),
            "payload": _safe_log_payload(body),
        }
        REQUEST_LOG.append(record)
        log_path = STATE.get("request_log")
        if log_path:
            Path(log_path).write_text(json.dumps(REQUEST_LOG, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return JSONResponse(body, status_code=status)

    @app.get("/assembly/api/custody-counts")
    def custody_counts():
        return STATE["world"].counts(STATE["case_id"])

    @app.get("/assembly/api/request-log")
    def request_log():
        return {"records": REQUEST_LOG}

    @app.get("/assembly/")
    def index():
        return FileResponse(assembly / "index.html")

    app.mount("/assembly", StaticFiles(directory=str(assembly), html=True), name="assembly")
    return app


def main() -> None:
    if len(sys.argv) < 6:
        raise SystemExit(
            "host.py <assembly> <materialized-source> <fixtures> <worktree> <core-cmd> <dll-sha> [host] [port] [request-log]"
        )
    assembly = Path(sys.argv[1])
    source = Path(sys.argv[2])
    fixtures = Path(sys.argv[3])
    worktree = Path(sys.argv[4])
    core_cmd = Path(sys.argv[5])
    dll_sha = sys.argv[6]
    host = sys.argv[7] if len(sys.argv) > 7 else "127.0.0.1"
    port = int(sys.argv[8]) if len(sys.argv) > 8 else 18783
    request_log = Path(sys.argv[9]) if len(sys.argv) > 9 else None
    if host != "127.0.0.1":
        raise SystemExit("host must be 127.0.0.1")
    # materialize is done by the runner; just open a fresh world and register originals.
    if not (source / "service").is_dir():
        raise SystemExit(f"materialized source missing under {source}")
    world = FrozenWorld(source)
    try:
        cid, pins = register_locked_pair(world, fixtures)
        counts = world.counts(cid)
        if counts["access"] != 0:
            raise SystemExit(f"Access must stay 0 after registration only, got {counts}")
        STATE.update({
            "world": world,
            "case_id": cid,
            "pins": pins,
            "core_cmd": core_cmd,
            "worktree": worktree,
            "dll_sha": dll_sha,
            "request_log": str(request_log) if request_log else "",
            "startupCounts": counts,
        })
        import uvicorn
        app = create_app(assembly)
        print(f"W12_RTR_READY={host}:{port}", flush=True)
        print(f"W12_RTR_ACCESS_AFTER_REGISTER={counts['access']}", flush=True)
        uvicorn.run(app, host=host, port=port, log_level="warning", access_log=False)
    finally:
        world.close()


if __name__ == "__main__":
    if not sys.flags.isolated:
        raise SystemExit("Use existing Python -I")
    main()
