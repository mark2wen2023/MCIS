"""Isolated loopback host: same-case pair select by confirmed labels only.

127.0.0.1 only. Two pairs are pre-registered in one temporary SQLite world
via frozen preview/commit. The client may name pair-a or pair-b; original
pins are not accepted. Official product write routes are not used.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIBLING = HERE.parent / "w12-registered-json-gap"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SIBLING))

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from pairs import (
    LABEL_A,
    PairSelectError,
    assemble_labeled_view,
    public_catalog,
    register_two_pairs,
    reject_if_pins_present,
    resolve_label,
)
from snapshot import FrozenWorld

STATE: dict = {}
REQUEST_LOG: list[dict] = []
MAX_DELAY_MS = 8000


def _world_home(materialized: Path) -> Path:
    root = materialized.parent / f"{materialized.name}-pairs"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    os.symlink(materialized / "service", root / "service", target_is_directory=True)
    return root


def _params(request: Request) -> dict[str, str]:
    return {k: v for k, v in request.query_params.items()}


def _safe_log_payload(payload: dict) -> dict:
    out = {k: payload[k] for k in payload if k != "view"}
    if payload.get("ok") and isinstance(payload.get("view"), dict):
        view = payload["view"]
        out["viewSummary"] = {
            "caseId": view.get("caseId"),
            "title": view.get("title"),
            "pairLabel": view.get("pairLabel") or payload.get("pairLabel"),
            "identityCount": len(view.get("registeredIdentities") or []),
            "hasMetrics": bool(view.get("baseline")),
        }
    return out


def _error_body(code: str, message: str, *, called: bool = False) -> dict:
    counts = STATE["world"].counts(STATE["case_id"])
    return {
        "ok": False,
        "reason": code,
        "message": message,
        "pairLabel": None,
        "view": None,
        "identities": None,
        "accessBefore": counts,
        "accessAfter": counts,
        "deltaAccess": 0,
        "entry": "_load_registered_pair",
        "called": called,
    }


def _flush_log() -> None:
    log_path = STATE.get("request_log")
    if log_path:
        Path(log_path).write_text(json.dumps(REQUEST_LOG, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _record(path: str, status: int, params: dict, body: dict, delay_ms: int = 0, *, event: str = "finish") -> dict:
    record = {
        "event": event,
        "t": time.time(),
        "path": path,
        "method": "GET",
        "status": status,
        "query": params,
        "pairLabel": body.get("pairLabel") or params.get("pair"),
        "delayMs": delay_ms,
        "accessBefore": body.get("accessBefore"),
        "accessAfter": body.get("accessAfter"),
        "deltaAccess": body.get("deltaAccess"),
        "ok": body.get("ok"),
        "reason": body.get("reason"),
        "identities": body.get("identities"),
        "coreAt120": body.get("coreAt120"),
        "entry": body.get("entry"),
        "called": body.get("called"),
        "payload": _safe_log_payload(body) if event == "finish" else {},
    }
    REQUEST_LOG.append(record)
    _flush_log()
    return record


def create_app(assembly: Path) -> FastAPI:
    app = FastAPI()

    @app.get("/assembly/api/pairs")
    def list_pairs():
        body = {
            "ok": True,
            "caseId": STATE["case_id"],
            "pairs": public_catalog(STATE["pins_by_label"]),
            "selection": "confirmed-labels-only",
            "acceptsPins": False,
        }
        return JSONResponse(body)

    @app.get("/assembly/api/view")
    async def labeled_view(request: Request):
        params = _params(request)
        delay_ms = 0
        raw_delay = params.get("delayMs") or params.get("delayms") or "0"
        _record("/assembly/api/view", 0, params, {"pairLabel": params.get("pair"), "ok": None}, 0, event="start")
        try:
            delay_ms = int(raw_delay)
        except ValueError:
            body = _error_body("BAD_DELAY", "delayMs must be an integer")
            _record("/assembly/api/view", 400, params, body)
            return JSONResponse(body, status_code=400)
        if delay_ms < 0 or delay_ms > MAX_DELAY_MS:
            body = _error_body("BAD_DELAY", "delayMs out of isolated-test range")
            _record("/assembly/api/view", 400, params, body)
            return JSONResponse(body, status_code=400)
        try:
            reject_if_pins_present(params)
            label = resolve_label(params.get("pair"))
            REQUEST_LOG[-1]["pairLabel"] = label
            REQUEST_LOG[-1]["delayMs"] = delay_ms
            _flush_log()
            bundle = assemble_labeled_view(
                STATE["world"],
                case_id=STATE["case_id"],
                label=label,
                pins_by_label=STATE["pins_by_label"],
                core_cmd=STATE["core_cmd"],
                worktree=STATE["worktree"],
                dll_sha=STATE["dll_sha"],
            )
        except PairSelectError as exc:
            body = _error_body(exc.code, exc.message, called=False)
            _record("/assembly/api/view", 400, params, body, delay_ms)
            return JSONResponse(body, status_code=400)
        # Real read and core already finished. Optional test delay is only
        # to hold the response so the browser can switch back to A.
        if delay_ms:
            await asyncio.sleep(delay_ms / 1000.0)
        body = bundle
        _record("/assembly/api/view", 200, params, body, delay_ms)
        return JSONResponse(body)

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

    @app.on_event("startup")
    def _announce_ready() -> None:
        host = STATE["bind_host"]
        port = STATE["bind_port"]
        pins = STATE["pins_by_label"]
        from materialize import SHA_A, SHA_B
        from pairs import SHA_A_PAIR_B
        print(f"W12_PAIR_SELECT_READY={host}:{port}", flush=True)
        print(f"W12_PAIR_SELECT_SHA_A={pins['pair-a'][0]['sourceSha256']}", flush=True)
        print(f"W12_PAIR_SELECT_SHA_B={pins['pair-a'][1]['sourceSha256']}", flush=True)
        print(f"W12_PAIR_SELECT_SHA_A_B={pins['pair-b'][0]['sourceSha256']}", flush=True)
        print(f"W12_PAIR_SELECT_SHA_B_B={pins['pair-b'][1]['sourceSha256']}", flush=True)
        print(f"W12_PAIR_SELECT_ACCESS_AFTER_REGISTER={STATE['access_after_register']}", flush=True)
        print(f"W12_PAIR_SELECT_SHA_A_PAIR_B_FIXED={SHA_A_PAIR_B}", flush=True)

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
    port = int(sys.argv[8]) if len(sys.argv) > 8 else 18785
    request_log = Path(sys.argv[9]) if len(sys.argv) > 9 else None
    if host != "127.0.0.1":
        raise SystemExit("host must be 127.0.0.1")
    if not (source / "service").is_dir():
        raise SystemExit(f"materialized source missing under {source}")

    world = FrozenWorld(_world_home(source))
    try:
        cid, pins_by_label = register_two_pairs(world, fixtures)
        counts = world.counts(cid)
        if counts["access"] != 0:
            raise SystemExit(f"Access must stay 0 after registration, counts={counts}")
        # Prove A originals still have locked digests after B was registered.
        a_pins = pins_by_label[LABEL_A]
        from materialize import SHA_A, SHA_B
        from pairs import SHA_A_PAIR_B
        if a_pins[0]["sourceSha256"] != SHA_A or a_pins[1]["sourceSha256"] != SHA_B:
            raise SystemExit("registering pair B overwrote pair A digests")
        STATE.update({
            "world": world,
            "case_id": cid,
            "pins_by_label": pins_by_label,
            "core_cmd": core_cmd,
            "worktree": worktree,
            "dll_sha": dll_sha,
            "request_log": str(request_log) if request_log else "",
        })
        STATE.update({
            "bind_host": host,
            "bind_port": port,
            "access_after_register": counts["access"],
        })
        import uvicorn
        app = create_app(assembly)
        uvicorn.run(app, host=host, port=port, log_level="warning", access_log=False)
    finally:
        world.close()


if __name__ == "__main__":
    if not sys.flags.isolated:
        raise SystemExit("Use existing Python -I")
    main()
