"""Test-only wrapper for the exact application's synthetic loopback service."""
import argparse
import os
import socket
from pathlib import Path
from unittest.mock import patch

import uvicorn
from fastapi.staticfiles import StaticFiles

p = argparse.ArgumentParser()
p.add_argument("fixture", type=Path)
p.add_argument("assets", type=Path)
p.add_argument("data", type=Path)
args = p.parse_args()
assert args.assets.is_dir() and args.data.is_dir()
assert not any(k.startswith("MCIS_") for k in os.environ)
os.environ.update(MCIS_SEED_DEMO="0", MCIS_AGENT_BASE_URL="http://127.0.0.1:9/v1",
                  MCIS_AGENT_MODEL="controlled-fake-not-real-model")
from mcis_service.agents import model_client
from mcis_service.config import Settings
from mcis_service.main import create_app

def deny_model_connect(*_a, **_kw):
    raise AssertionError("No outbound sockets permitted in test host")

cfg = Settings(data_dir=args.data, db_url=f"sqlite:///{args.data / 'acceptance.sqlite'}")
app = create_app(cfg)
app.mount("/", StaticFiles(directory=args.assets, html=True), name="w20-exact-bundle")
with socket.socket() as server:
    server.bind(("127.0.0.1", 0))
    server.listen(128)
    print(f"W20_LOOPBACK_PORT={server.getsockname()[1]}", flush=True)
    # The accepted local socket remains usable. No outbound socket connections in this process.
    with patch.object(model_client, "complete", return_value=args.fixture.read_text()), \
         patch.object(socket.socket, "connect", deny_model_connect), \
         patch.object(socket.socket, "connect_ex", deny_model_connect), \
         patch.object(socket, "getaddrinfo", deny_model_connect):
        uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", log_level="warning", access_log=False)).run(sockets=[server])
