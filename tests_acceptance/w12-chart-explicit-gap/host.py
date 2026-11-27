"""Loopback host: MCIS service + isolated chart-gap assembly. Never deploy. Bind 127.0.0.1 only."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn
from fastapi.staticfiles import StaticFiles

assets, store, seed, sidecar, assembly = map(Path, sys.argv[1:6])
host = sys.argv[6]
port = int(sys.argv[7])
service_root = Path(sys.argv[8]).resolve()
assert host == "127.0.0.1", "service must bind loopback only"
assert seed.is_file() and sidecar.is_file()
assert assembly.is_dir() and (assembly / "index.html").is_file()
assert not any(k.startswith("MCIS_") for k in os.environ)

sys.path.insert(0, str(service_root))
import mcis_service.analysis.router as analysis_mod
from mcis_service.config import Settings
from mcis_service.main import create_app

_orig = analysis_mod.load_seed

def load_seed(path=seed, sidecar=sidecar):
    return _orig(path, sidecar)

analysis_mod.load_seed = load_seed
analysis_mod.SEED = seed
analysis_mod.SIDECAR = sidecar
analysis_mod._cache.clear()

store.mkdir(parents=True, exist_ok=True)
cfg = Settings(data_dir=store, db_url=f"sqlite:///{store / 'acceptance.sqlite'}", seed_demo=False)
app = create_app(cfg)
# Isolated assembly is the official page. Product UI is not required for this check.
app.mount("/assembly", StaticFiles(directory=assembly, html=True), name="w12-chart-gap-assembly")
if assets.is_dir() and (assets / "index.html").is_file():
    app.mount("/", StaticFiles(directory=assets, html=True), name="optional-product-ui")
print(f"W12_LOOPBACK={host}:{port}", flush=True)
uvicorn.run(app, host=host, port=port, log_level="warning", access_log=False)
