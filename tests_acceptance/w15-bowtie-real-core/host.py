"""Ephemeral localhost HTTP host for the original W15 service and real core."""
import os
from pathlib import Path
import socket
import sys

import uvicorn

from mcis_service.config import Settings
from mcis_service.main import create_app

assert Path(os.environ["MCIS_DOTNET"]).is_file()
assert {s.split(":", 1)[0].strip()
        for s in Path("/proc/net/dev").read_text().splitlines()[2:] if ":" in s} == {"lo"}
store = Path(sys.argv[1])
assert store.is_dir()
cfg = Settings(data_dir=store, db_url=f"sqlite:///{store / 'acceptance.sqlite'}", seed_demo=False)
app = create_app(cfg)
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    sock.listen(64)
    print(f"W15_CORE_PORT={sock.getsockname()[1]}", flush=True)
    uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", log_level="warning", access_log=False)).run(sockets=[sock])
