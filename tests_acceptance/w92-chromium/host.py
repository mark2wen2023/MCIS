"""Loopback-only W9.2 test host with original case and environment routers."""
import argparse
import ast
import json
from pathlib import Path
import socket
import sys
from unittest.mock import patch

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

P = argparse.ArgumentParser()
P.add_argument("source", type=Path)
P.add_argument("assets", type=Path)
P.add_argument("database", type=Path)
P.add_argument("fixture", type=Path)
P.add_argument("--audit-only", action="store_true")
A = P.parse_args()
sys.path.insert(0, str(A.source / "service"))

from mcis_service.audit import service as audit
from mcis_service.audit.models import AuditEventRow
from mcis_service.cases.router import router as cases
from mcis_service.db import Base, Database
from mcis_service.environment.models import EnvironmentObservationRow
from mcis_service.environment.router import router as environment

if not __debug__:
    raise SystemExit("Assertions must be enabled")
record = json.loads(A.fixture.read_text())
db = Database(f"sqlite:///{A.database}")
try:
    if A.audit_only:
        assert A.database.is_file()
        with db.session() as session:
            rows = list(session.scalars(select(EnvironmentObservationRow)))
            assert len(rows) == 1
            assert rows[0].doc == record
            assert rows[0].case_id == record["caseId"] and rows[0].key == record["observationId"]
            entries = list(session.scalars(select(AuditEventRow).where(
                AuditEventRow.action == "environment.observation.create")))
            assert len(entries) == 1
            entry = entries[0]
            assert entry.case_id == record["caseId"] and entry.entity_id == record["observationId"]
            assert entry.entity_type == "environmentObservation"
            assert entry.role == "Investigator" and entry.operator == "synthetic-ui"
            assert ast.literal_eval(entry.after) == record
            assert audit.verify_chain(audit.all_lines(session, record["caseId"]))["valid"] is True
        print('{"observationRows":1,"observationWriteAuditRows":1,"auditChainValid":true}')
    else:
        Base.metadata.create_all(db.engine)
        app = FastAPI()
        app.state.db = db
        app.include_router(cases)
        app.include_router(environment)
        app.mount("/assets", StaticFiles(directory=A.assets), name="w92-assets")

        @app.get("/environment")
        def shell():
            from fastapi.responses import FileResponse
            return FileResponse(A.assets / "index.html")

        def deny_outbound(*_args, **_kwargs):
            raise AssertionError("Outbound network is not allowed in the fixture service")

        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            sock.listen(64)
            print(f"W92_PORT={sock.getsockname()[1]}", flush=True)
            with patch.object(socket.socket, "connect", deny_outbound), \
                 patch.object(socket.socket, "connect_ex", deny_outbound), \
                 patch.object(socket, "getaddrinfo", deny_outbound):
                uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False)).run(sockets=[sock])
finally:
    db.engine.dispose()
