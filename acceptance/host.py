"""Isolated loopback host: import registered tracks, serve assembly API. Never deploy. 127.0.0.1 only."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

import uvicorn
from fastapi.staticfiles import StaticFiles

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from build_view import complete_case, missing_payload  # noqa: E402
from live_seed import write_seed  # noqa: E402
from registered_read import (  # noqa: E402
    CASE_MISS,
    CASE_OK,
    COMMON_TIMES,
    OUTSIDE_TIMES,
    OWN,
    TARGET,
    Http,
    capture_in_one_transaction,
    create_and_import,
    csv_bytes,
    metrics_for_common_samples,
    OWN_ROWS,
    TGT_ROWS,
)


def main() -> int:
    assembly, store, report_official, service_root, wrapper, core_dir = map(Path, sys.argv[1:7])
    host = sys.argv[7]
    port = int(sys.argv[8])
    assert host == "127.0.0.1", "service must bind loopback only"
    assert assembly.is_dir() and (assembly / "index.html").is_file()
    store.mkdir(parents=True, exist_ok=True)
    report_official.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(service_root.resolve()))
    seed, sidecar, seed_sha = write_seed(report_official / "live-seed")
    import mcis_service.analysis.router as analysis_mod
    from mcis_service.colreg import core_client
    from mcis_service.config import Settings
    from mcis_service.main import create_app

    _orig = analysis_mod.load_seed

    def load_seed(path=seed, sidecar=sidecar):
        return _orig(path, sidecar)

    analysis_mod.load_seed = load_seed
    analysis_mod.SEED = seed
    analysis_mod.SIDECAR = sidecar
    analysis_mod._cache.clear()

    cfg = Settings(
        data_dir=store,
        db_url=f"sqlite:///{store / 'acceptance.sqlite'}",
        seed_demo=False,
        core_cmd=str(wrapper),
        host=host,
        port=port,
    )
    app = create_app(cfg)

    state: dict = {"ready": False}

    @app.get("/assembly/api/registered")
    def registered_view():
        if not state.get("ready"):
            return {"error": "not-ready"}
        capture = capture_in_one_transaction(app, CASE_OK, [OWN, TARGET], state["digests_ok"])
        if not capture["ok"]:
            return {"error": "capture-failed", "reason": capture.get("reason")}
        core = metrics_for_common_samples(
            capture["identities"], capture["points"], core_client.run, str(wrapper),
            list(COMMON_TIMES) + list(OUTSIDE_TIMES),
        )
        missing = capture_in_one_transaction(app, CASE_MISS, [OWN, TARGET], {OWN: state["digests_miss"][OWN]})
        return {
            "complete": complete_case(capture, core, state["dll_sha"], [0.0, 10.0, 15.0, 20.0, 30.0, 40.0]),
            "missing": missing_payload(missing),
            "liveSeedSha256": seed_sha,
        }

    app.mount("/assembly", StaticFiles(directory=assembly, html=True), name="w12-frw-assembly")

    def serve():
        uvicorn.run(app, host=host, port=port, log_level="warning", access_log=False)

    thread = threading.Thread(target=serve, name="w12-frw-host", daemon=True)
    thread.start()
    http = Http(f"http://{host}:{port}/api/v1")
    deadline = time.time() + 20
    last = None
    while time.time() < deadline:
        try:
            status, body = http.call("/health")
            if status == 200 and isinstance(body, dict) and body.get("status") == "ok":
                break
            last = (status, body)
        except Exception as exc:  # noqa: BLE001
            last = str(exc)
        time.sleep(0.05)
    else:
        print(f"health failed: {last}", file=sys.stderr)
        return 2

    own_raw, tgt_raw = csv_bytes(OWN_ROWS), csv_bytes(TGT_ROWS)
    (report_official / "fixtures").mkdir(parents=True, exist_ok=True)
    (report_official / "fixtures" / "own.csv").write_bytes(own_raw)
    (report_official / "fixtures" / "target.csv").write_bytes(tgt_raw)
    digests_ok = create_and_import(http, CASE_OK, [(OWN, own_raw), (TARGET, tgt_raw)])
    digests_miss = create_and_import(http, CASE_MISS, [(OWN, own_raw)])
    status, body = http.call(
        f"/cases/{CASE_MISS}/vessels",
        {"vesselId": TARGET, "caseId": CASE_MISS, "name": f"Synthetic {TARGET}"},
        method="POST",
    )
    if status != 201:
        print(f"incomplete second vessel failed: {status} {body}", file=sys.stderr)
        return 2
    dll = os.environ["MCIS_CORE_DLL"]
    import hashlib
    dll_sha = hashlib.sha256(Path(dll).read_bytes()).hexdigest()
    state.update(digests_ok=digests_ok, digests_miss=digests_miss, dll_sha=dll_sha, ready=True)

    capture = capture_in_one_transaction(app, CASE_OK, [OWN, TARGET], digests_ok)
    core = metrics_for_common_samples(
        capture["identities"], capture["points"], core_client.run, str(wrapper),
        list(COMMON_TIMES) + list(OUTSIDE_TIMES),
    )
    missing = capture_in_one_transaction(app, CASE_MISS, [OWN, TARGET], {OWN: digests_miss[OWN]})
    (report_official / "import-digests.json").write_text(
        json.dumps({"complete": digests_ok, "incomplete": digests_miss}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (report_official / "capture-complete.json").write_text(
        json.dumps({
            "ok": capture["ok"], "reason": capture["reason"],
            "identities": capture.get("identities"), "commonTimes": capture.get("commonTimes"),
            "transaction": capture.get("transaction"),
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (report_official / "core-metrics.json").write_text(
        json.dumps({
            "coreVersion": core.get("coreVersion"),
            "recalculatedIdentical": core.get("recalculatedIdentical"),
            "metrics": core.get("metrics"),
            "requestedTimes": core.get("requestedTimes"),
            "missingTimes": core.get("missingTimes"),
            "reason": core.get("reason"),
            "dllSha256": dll_sha,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (report_official / "capture-missing.json").write_text(
        json.dumps(missing_payload(missing), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"W12_FRW_READY={host}:{port} seed={seed_sha} dll={dll_sha}", flush=True)
    thread.join()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        import traceback
        traceback.print_exc()
        raise SystemExit(2)
