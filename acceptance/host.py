"""Loopback host for W12 snapshot-scope browser control. Never deploy."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn
from fastapi.staticfiles import StaticFiles

assets, store, seed, sidecar = map(Path, sys.argv[1:5])
host = sys.argv[5]
port = int(sys.argv[6])
assert host == "127.0.0.1", "service must bind loopback only"
assert assets.is_dir() and (assets / "index.html").is_file()
assert seed.is_file() and sidecar.is_file()
assert not any(k.startswith("MCIS_") for k in os.environ)

sys.path.insert(0, str(Path(sys.argv[7]).resolve()))
import mcis_service.analysis.router as analysis_mod
from mcis_service.config import Settings
from mcis_service.main import create_app

# load_seed defaults bind the product SEED path at import time; replace the function.
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
app.mount("/", StaticFiles(directory=assets, html=True), name="fixed-product-ui")
print(f"W12_LOOPBACK={host}:{port}", flush=True)
uvicorn.run(app, host=host, port=port, log_level="warning", access_log=False)
