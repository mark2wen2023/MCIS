"""Isolated, synthetic W15.3 service; never deploy this host."""
import os
import socket
import sys
from pathlib import Path
from unittest.mock import patch

import uvicorn
from fastapi.staticfiles import StaticFiles

assets, store = map(Path, sys.argv[1:])
assert assets.is_dir() and store.is_dir()
assert not any(k.startswith("MCIS_") for k in os.environ)
os.environ.update(MCIS_SEED_DEMO="0", MCIS_DOTNET=str(store / "intentionally-absent-sdk"))
from mcis_service.config import Settings
from mcis_service.main import create_app

def deny_network(*args, **kwargs):
    raise AssertionError("Outbound connection not allowed in synthetic test host")

cfg = Settings(data_dir=store, db_url=f"sqlite:///{store / 'acceptance.sqlite'}", seed_demo=False)
app = create_app(cfg)
app.mount("/", StaticFiles(directory=assets, html=True), name="fixed-product-ui")
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    print(f"W15_LOOPBACK_PORT={sock.getsockname()[1]}", flush=True)
    with patch.object(socket.socket, "connect", deny_network), \
         patch.object(socket.socket, "connect_ex", deny_network), \
         patch.object(socket, "getaddrinfo", deny_network):
        uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", log_level="warning", access_log=False)).run(sockets=[sock])
