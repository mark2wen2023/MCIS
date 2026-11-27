"""Official MCIS loopback host for the W7 same-page round-switch gate.

Listens on 127.0.0.1 only. Temporary data directory, no demo seed.
Product code is unchanged.
"""
from __future__ import annotations

import os
from pathlib import Path

import uvicorn
from mcis_service.config import Settings
from mcis_service.main import create_app

DATA = Path(os.environ["MCIS_DATA_DIR"])
PORT = int(os.environ.get("MCIS_PORT", "18792"))
HOST = "127.0.0.1"

app = create_app(Settings(data_dir=DATA, seed_demo=False, host=HOST, port=PORT))


@app.on_event("startup")
def _ready() -> None:
    print(f"W7_ROUND_SWITCH_READY port={PORT}", flush=True)


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
