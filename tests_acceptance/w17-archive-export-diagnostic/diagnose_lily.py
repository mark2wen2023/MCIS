import json
import tempfile
from pathlib import Path
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text
from mcis_service.cases.models import CaseRow
from mcis_service.config import Settings
from mcis_service.main import create_app
from mcis_service.package.mcase import export_case
from mcis_service.seed.lily_mary import CASE_ID, seed
from tests.test_working_record_archive import HEAD, snapshot
from mcis_service.working_records_archive.service import ALLOWED_TABLES, GLOBALS

with tempfile.TemporaryDirectory(prefix="w17-synthetic-demo-") as d:
    root=Path(d)
    app=create_app(Settings(data_dir=root,db_url=f"sqlite:///{root/'test.db'}",seed_demo=False))
    blobs=app.state.settings.blob_dir
    with app.state.db.session() as s:
        assert seed(s,blobs) is True
        assert [(r.case_id,r.doc["isFictionalDemo"]) for r in s.scalars(select(CaseRow))] == [(CASE_ID,True)]
    def files():
        return {str(p.relative_to(blobs)):p.read_bytes() for p in blobs.rglob("*") if p.is_file()}
    with TestClient(app) as c:
        before,bfiles=snapshot(c),files()
        result=c.get(f"/api/v1/cases/{CASE_ID}/export",headers=HEAD)
        assert result.status_code==409,result.status_code
        assert result.json()=={"code":"ARCHIVE_RESTORE_UNSUPPORTED","message":"此案未通过完整恢复预检，未生成部分案件包"}
        assert snapshot(c)==before and files()==bfiles
        unsupported = []
        with app.state.db.session() as s:
            inspector = inspect(s.connection())
            for name in inspector.get_table_names():
                if name in ALLOWED_TABLES or name in GLOBALS:
                    continue
                columns = {c["name"] for c in inspector.get_columns(name)}
                quoted = '"' + name.replace('"','""') + '"'
                count = s.execute(text("SELECT COUNT(*) FROM "+quoted+(" WHERE case_id=:case_id" if "case_id" in columns else "")),{"case_id":CASE_ID}).scalar_one()
                if count:
                    unsupported.append((name,count))
            try:
                export_case(s,blobs,CASE_ID,"Synthetic internal replay","LeadInvestigator")
            except HTTPException as err:
                assert isinstance(err.__cause__,HTTPException)
                current=err
                chain=[]
                while isinstance(current,HTTPException):
                    chain.append((current.status_code,current.detail))
                    current=current.__cause__
                s.rollback()
            else:
                raise AssertionError("Expected existing synthetic seed to fail closed")
        assert snapshot(c)==before and files()==bfiles
        print(json.dumps({"caseId":CASE_ID,"public":result.json(),"isolatedCause":chain,"unsupportedNonempty":unsupported},ensure_ascii=False))
