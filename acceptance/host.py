"""Isolated loopback host: both allow and deny contexts call frozen _load_registered_pair.

127.0.0.1 only. Synthetic test role contexts select an independent policy-seeded
world; they are not real identity authentication and must not pre-answer 403.
One response carries only that context's result; pins stay on the server.
"""
from __future__ import annotations

import os
import shutil
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
from view import (
    assemble_authorized_view,
    attempt_policy_denied_load,
    register_locked_pair,
    seed_synthetic_deny_policy,
)

# Synthetic test-server context names. Not real authentication.
# They select which independent seeded world handles the GET; both worlds
# still call the same frozen _load_registered_pair entry.
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
        "roleContextNote": "合成测试服务端角色上下文，不是真实身份认证；本请求实际调用了冻结 _load_registered_pair",
        "view": view,
        "sampleStatus": bundle["sampleStatus"],
        "coreVersion": bundle["coreVersion"],
        "dllSha256": bundle["dllSha256"],
        "declaredOpenGaps": bundle["declaredOpenGaps"],
        "accessBefore": bundle["accessBefore"],
        "accessAfter": bundle["accessAfter"],
        "deltaAccess": bundle["deltaAccess"],
        "policyResult": {
            "entry": "_load_registered_pair",
            "called": True,
            "outcome": "allowed",
            "seed": "default_policy Investigator evidence_meta=ReadWrite",
            "exceptionType": None,
            "statusCode": None,
            "detail": None,
        },
    }


def _denied_body(*, reason: str, before: dict, after: dict, role: str, policy_result: dict | None) -> dict:
    return {
        "ok": False,
        "reason": reason,
        "roleContext": role,
        "roleContextKind": ROLE_KIND,
        "roleContextNote": "合成测试服务端角色上下文，不是真实身份认证；拒绝须来自冻结读取入口的证据策略",
        "metricsReturned": False,
        "currentAnalysis": None,
        "view": None,
        "registeredIdentities": None,
        "accessBefore": before,
        "accessAfter": after,
        "deltaAccess": after["access"] - before["access"],
        "policyResult": policy_result,
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


def _world_home(materialized: Path, name: str) -> Path:
    """Independent runtime + sqlite; reuse the same frozen service tree."""
    root = materialized.parent / f"{materialized.name}-{name}"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    os.symlink(materialized / "service", root / "service", target_is_directory=True)
    return root


def create_app(assembly: Path) -> FastAPI:
    app = FastAPI()

    @app.get("/assembly/api/view")
    def request_time_view(request: Request):
        role = _role_of(request)
        if role == ROLE_AUTHORIZED:
            world = STATE["world_allow"]
            cid = STATE["case_allow"]
            pins = STATE["pins_allow"]
            bundle = assemble_authorized_view(
                world,
                case_id=cid,
                pins=pins,
                core_cmd=STATE["core_cmd"],
                worktree=STATE["worktree"],
                dll_sha=STATE["dll_sha"],
            )
            body = _public_authorized(bundle)
            status = 200
        elif role == ROLE_DENIED:
            world = STATE["world_deny"]
            cid = STATE["case_deny"]
            pins = STATE["pins_deny"]
            bundle = attempt_policy_denied_load(world, case_id=cid, pins=pins)
            body = _denied_body(
                reason=bundle["reason"],
                before=bundle["accessBefore"],
                after=bundle["accessAfter"],
                role=ROLE_DENIED,
                policy_result=bundle["policyResult"],
            )
            status = 403
        else:
            # Do not call the frozen entry or invent a policy-deny 403.
            counts = STATE["world_allow"].counts(STATE["case_allow"])
            body = _denied_body(
                reason="missing-synthetic-role-context",
                before=counts,
                after=counts,
                role=role,
                policy_result={
                    "entry": "_load_registered_pair",
                    "called": False,
                    "outcome": "no-context",
                    "seed": None,
                    "exceptionType": None,
                    "statusCode": None,
                    "detail": None,
                },
            )
            status = 400
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
            "policyResult": body.get("policyResult"),
            "payload": _safe_log_payload(body),
        }
        REQUEST_LOG.append(record)
        log_path = STATE.get("request_log")
        if log_path:
            import json
            Path(log_path).write_text(json.dumps(REQUEST_LOG, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return JSONResponse(body, status_code=status)

    @app.get("/assembly/api/custody-counts")
    def custody_counts(request: Request):
        role = _role_of(request)
        if role == ROLE_DENIED:
            return STATE["world_deny"].counts(STATE["case_deny"])
        return STATE["world_allow"].counts(STATE["case_allow"])

    @app.get("/assembly/api/request-log")
    def request_log():
        return {"records": REQUEST_LOG}

    @app.get("/assembly/")
    def index():
        return FileResponse(assembly / "index.html")

    app.mount("/assembly", StaticFiles(directory=str(assembly), html=True), name="assembly")
    return app


def main() -> None:
    if len(sys.argv) < 7:
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
    port = int(sys.argv[8]) if len(sys.argv) > 8 else 18784
    request_log = Path(sys.argv[9]) if len(sys.argv) > 9 else None
    if host != "127.0.0.1":
        raise SystemExit("host must be 127.0.0.1")
    if not (source / "service").is_dir():
        raise SystemExit(f"materialized source missing under {source}")

    world_allow = FrozenWorld(_world_home(source, "allow"))
    world_deny = FrozenWorld(_world_home(source, "deny"))
    try:
        cid_allow, pins_allow = register_locked_pair(world_allow, fixtures)
        cid_deny, pins_deny = register_locked_pair(world_deny, fixtures)
        if cid_allow != cid_deny:
            raise SystemExit("allow/deny caseId mismatch")
        seed_synthetic_deny_policy(world_deny, cid_deny)
        allow_counts = world_allow.counts(cid_allow)
        deny_counts = world_deny.counts(cid_deny)
        if allow_counts["access"] != 0 or deny_counts["access"] != 0:
            raise SystemExit(f"Access must stay 0 after registration/seed, allow={allow_counts} deny={deny_counts}")
        STATE.update({
            "world_allow": world_allow,
            "world_deny": world_deny,
            "case_allow": cid_allow,
            "case_deny": cid_deny,
            "pins_allow": pins_allow,
            "pins_deny": pins_deny,
            "core_cmd": core_cmd,
            "worktree": worktree,
            "dll_sha": dll_sha,
            "request_log": str(request_log) if request_log else "",
        })
        import uvicorn
        app = create_app(assembly)
        print(f"W12_RTR_READY={host}:{port}", flush=True)
        print(f"W12_RTR_ACCESS_AFTER_REGISTER_ALLOW={allow_counts['access']}", flush=True)
        print(f"W12_RTR_ACCESS_AFTER_SEED_DENY={deny_counts['access']}", flush=True)
        uvicorn.run(app, host=host, port=port, log_level="warning", access_log=False)
    finally:
        world_allow.close()
        world_deny.close()


if __name__ == "__main__":
    if not sys.flags.isolated:
        raise SystemExit("Use existing Python -I")
    main()
