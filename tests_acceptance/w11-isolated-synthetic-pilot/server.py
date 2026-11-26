"""Loopback-only isolated pilot host. Never a product entry point."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

def _parse():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-dir", type=Path, required=True)
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--enable-pilot", action="store_true")
    p.add_argument("--routes-out", type=Path, required=True)
    p.add_argument("--ready-file", type=Path, required=True)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--service-root", type=Path, required=True)
    p.add_argument("--excerpt-binding", type=Path, required=True)
    p.add_argument("--edge-host", type=Path, required=True)
    return p.parse_args()

def _route_rows(app):
    rows = []
    for route in app.routes:
        methods = sorted(getattr(route, "methods", None) or [])
        path = getattr(route, "path", None)
        if path:
            rows.append({"path": path, "methods": methods})
    rows.sort(key=lambda r: (r["path"], r["methods"]))
    return rows

def main():
    if not __debug__:
        raise SystemExit("Assertions must be enabled")
    args = _parse()
    if args.host != "127.0.0.1":
        raise SystemExit("Pilot host must bind 127.0.0.1 only")
    if args.port < 1 or args.port > 65535:
        raise SystemExit("Invalid port")
    for path in (args.service_root, args.excerpt_binding, args.edge_host):
        if not path.is_dir():
            raise SystemExit(f"Missing reuse directory: {path}")
    sys.path[:0] = [str(args.service_root), str(args.excerpt_binding), str(args.edge_host)]
    from mcis_service.config import PROJECT_ROOT, Settings
    from mcis_service.ecfc_drafts import router as ec
    from mcis_service.main import create_app
    from host import PATH, setup

    cli = Path(ec.CLI).resolve()
    expected = (PROJECT_ROOT / "tools" / "mcis-ecfc" / "mcis-ecfc.sh").resolve()
    if cli != expected or not cli.is_file():
        raise SystemExit(f"ECFC launcher mismatch: {cli}")
    if "mcis-w11-isolated-cand" in str(cli) or "maritime-sim-design" in str(cli):
        raise SystemExit(f"Refusing to invoke worktree/product launcher: {cli}")

    args.data_dir.mkdir(parents=True, exist_ok=True)
    cfg = Settings(data_dir=args.data_dir, db_url=f"sqlite:///{args.db}", seed_demo=False)
    app = create_app(cfg)
    official = _route_rows(app)
    paths = {row["path"] for row in official}
    if PATH in paths:
        raise SystemExit("Official create_app registered the pilot excerpt route")
    if args.enable_pilot:
        setup(app)
        if PATH not in {row["path"] for row in _route_rows(app)}:
            raise SystemExit("Pilot setup did not register the excerpt route")
    args.routes_out.write_text(json.dumps({
        "enablePilot": bool(args.enable_pilot),
        "pilotPath": PATH,
        "officialPathsContainPilot": PATH in paths,
        "officialRoutes": official,
        "routesAfterSetup": _route_rows(app) if args.enable_pilot else official,
        "cli": str(cli),
        "projectRoot": str(Path(PROJECT_ROOT).resolve()),
        "bind": {"host": args.host, "port": args.port},
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.ready_file.write_text(json.dumps({
        "host": args.host, "port": args.port, "pid": os.getpid(),
        "enablePilot": bool(args.enable_pilot),
    }) + "\n", encoding="utf-8")
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")

if __name__ == "__main__":
    raise SystemExit(main())
