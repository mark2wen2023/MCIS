"""Official MCIS loopback host for the W9 official ships-page read gate.

Listens on 127.0.0.1 only. Temporary data directory, no demo seed.
Product code is unchanged. Writes are logged separately from reads.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import uvicorn
from mcis_service.config import Settings
from mcis_service.main import create_app
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

DATA = Path(os.environ["MCIS_DATA_DIR"])
PORT = int(os.environ.get("MCIS_PORT", "18798"))
HOST = "127.0.0.1"
WRITE_LOG = Path(os.environ["MCIS_WRITE_LOG"])

app = create_app(Settings(data_dir=DATA, seed_demo=False, host=HOST, port=PORT))


class ObserveWrites(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        rec = {
            "method": request.method,
            "path": request.url.path,
            "query": request.url.query,
            "status": response.status_code,
        }
        WRITE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with WRITE_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return response


app.add_middleware(ObserveWrites)


@app.on_event("startup")
def _ready() -> None:
    print(f"W9_SHIPS_PAGE_READY port={PORT}", flush=True)


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
