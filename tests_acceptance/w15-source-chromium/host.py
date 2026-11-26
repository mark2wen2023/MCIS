"""Isolated, synthetic W15.3 service; never deploy this host."""
import hashlib
import os
import socket
import sys
import time
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
class ObservePreview:
    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        if (scope["type"] != "http" or scope["method"] != "POST"
                or not scope["path"].endswith("/systemic/bowtie:preview")):
            return await self.application(scope, receive, send)
        digest = hashlib.sha256()
        count = 0
        print(f"W15 HOST t={time.monotonic():.6f} preview request", file=sys.stderr, flush=True)

        async def observe(message):
            nonlocal count
            await send(message)
            if message["type"] == "http.response.start":
                print(f"W15 HOST t={time.monotonic():.6f} preview sent_headers status={message['status']}",
                      file=sys.stderr, flush=True)
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                digest.update(body)
                count += len(body)
                if not message.get("more_body", False):
                    print(f"W15 HOST t={time.monotonic():.6f} preview sent_final bytes={count} "
                          f"sha256={digest.hexdigest()}", file=sys.stderr, flush=True)
        await self.application(scope, receive, observe)

with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    print(f"W15_LOOPBACK_PORT={sock.getsockname()[1]}", flush=True)
    with patch.object(socket.socket, "connect", deny_network), \
         patch.object(socket.socket, "connect_ex", deny_network), \
         patch.object(socket, "getaddrinfo", deny_network):
        uvicorn.Server(uvicorn.Config(ObservePreview(app), host="127.0.0.1", log_level="warning", access_log=False)).run(sockets=[sock])
