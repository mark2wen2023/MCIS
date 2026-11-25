"""Synthetic, private real-core preview/save/reopen; never invoke fixture graph()."""
from hashlib import sha256
import json
from pathlib import Path
import socket
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select
from mcis_service.config import Settings

# This imports existing helpers; the synthetic fixture core function is not called or installed.
from check import CASE, EDGE, SOURCE_SHA, ec, no_net, open_store, seed

def run(raw, tree):
    assert ec.CLI.resolve() == tree / "tools/mcis-ecfc/mcis-ecfc.sh"
    assert sha256(raw).hexdigest() == SOURCE_SHA
    with TemporaryDirectory(prefix="w11-synthetic-") as data:
        data = Path(data)
        cfg = Settings(data_dir=data, db_url=f"sqlite:///{data/'pilot.sqlite'}", seed_demo=False)
        app, ctx = open_store(cfg)
        try:
            with TestClient(app) as client:
                receipt = seed(client, raw)
                edge = dict(zip(("id","from","to"), EDGE, strict=True))
                nodes = [
                    dict(id=EDGE[1],kind="Condition",text="Synthetic condition",timeSeconds=None,
                         lane=0,isPrimaryIncident=False,evidenceIds=["EV-001"]),
                    dict(id=EDGE[2],kind="Event",text="Synthetic unknown event",timeSeconds=None,
                         lane=0,isPrimaryIncident=False,evidenceIds=[]),
                ]
                draft = dict(scope="Synthetic edge, no finding", nodes=nodes, edges=[edge])
                expected = [dict(evidenceId="EV-001", title=receipt["metadata"]["title"], sha256=SOURCE_SHA)]
                preview, sources = ec.validate_body(dict(draft=draft, expectedSources=expected),preview=True)
                result = ec.preview_sync(ctx,CASE,preview,sources)
                assert result["persisted"] is False and result["caseId"] == CASE
                assert result["validation"]["coreVersion"] == "mcis-ecfc-draft/1"
                assert result["validation"]["edges"] == [{**edge, "kind":"Influence", "bold":False}]
                peek = ec.get_draft(CASE,ctx)
                assert peek.status_code == 200 and json.loads(peek.body)["document"] is None
                body, sources = ec.validate_body(dict(
                    requestId="6bff10c5-3381-4fcc-8c53-a1120bba0cee",expectedDigest=None,
                    draft=draft, expectedSources=expected, acknowledgeArchiveLimitation=True))
                saved = ec.save_sync(ctx,CASE,body,sources)["document"]
                assert saved["revision"] == 1 and saved["status"] == "Draft" and saved["strength"] == "ToBeVerified"
        finally:
            app.state.db.engine.dispose()
        app, ctx = open_store(cfg)
        try:
            with TestClient(app):
                response = ec.get_draft(CASE,ctx)
                assert response.status_code == 200
                assert json.loads(response.body)["document"] == saved
                with ctx.db.session() as session:
                    audit = session.scalars(select(ec.EcfcAuditRow).where(ec.EcfcAuditRow.case_id==CASE)).all()
                    requests = session.scalars(select(ec.EcfcRequestRow).where(ec.EcfcRequestRow.case_id==CASE)).all()
                    assert len(audit) == len(requests) == 1
                    assert audit[0].doc["after"] == saved
        finally:
            app.state.db.engine.dispose()

if __name__ == "__main__":
    assert __debug__
    with patch.object(socket.socket,"connect",no_net), patch.object(socket.socket,"connect_ex",no_net), patch.object(socket,"getaddrinfo",no_net):
        run(Path(sys.argv[1]).read_bytes(),Path(sys.argv[2]).resolve())
    print("W11 actual ECFC core synthetic preview/save/SQLite reopen PASS; not browser, association, archive, or production")
