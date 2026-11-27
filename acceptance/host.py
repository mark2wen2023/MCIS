"""Isolated loopback host: frozen allowlist registration + read-only AnalysisView snapshot. 127.0.0.1 only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

STATE: dict = {}


def create_app(assembly: Path, snapshot: dict) -> FastAPI:
    app = FastAPI()
    public = {
        "complete": snapshot["complete"],
        "sampleStatus": snapshot["sampleStatus"],
        "denied": snapshot["denied"],
        "unpaired": snapshot["unpaired"],
        "successAccess": snapshot["successAccess"],
        "fixtureSha256": snapshot["fixtureSha256"],
        "coreVersion": snapshot["coreVersion"],
        "declaredOpenGaps": snapshot["declaredOpenGaps"],
    }

    @app.get("/assembly/api/registered")
    def registered_view():
        return public

    @app.get("/assembly/api/custody-counts")
    def custody_counts():
        world = STATE["world"]
        cid = snapshot["complete"]["caseId"]
        return world.counts(cid)

    @app.get("/assembly/")
    def index():
        return FileResponse(assembly / "index.html")

    app.mount("/assembly", StaticFiles(directory=str(assembly), html=True), name="assembly")
    return app


def main() -> None:
    if len(sys.argv) < 4:
        raise SystemExit("host.py <assembly> <snapshot.json> <materialized-source> [host] [port]")
    assembly = Path(sys.argv[1])
    snap_path = Path(sys.argv[2])
    source = Path(sys.argv[3])
    host = sys.argv[4] if len(sys.argv) > 4 else "127.0.0.1"
    port = int(sys.argv[5]) if len(sys.argv) > 5 else 18782
    if host != "127.0.0.1":
        raise SystemExit("host must be 127.0.0.1")
    snapshot = json.loads(snap_path.read_text(encoding="utf-8"))
    from snapshot import FrozenWorld
    world = FrozenWorld.attach(source)
    STATE["world"] = world
    import uvicorn
    app = create_app(assembly, snapshot)
    print(f"W12_RJG_READY={host}:{port}", flush=True)
    try:
        uvicorn.run(app, host=host, port=port, log_level="warning", access_log=False)
    finally:
        world.close()


if __name__ == "__main__":
    main()
