"""Diagnostic probe (outside repo): same race as test_policy_and_audit_are_one_snapshot, but surfaces the server exception."""
import sys,tempfile,traceback
from pathlib import Path
sys.path.insert(0,'.');sys.path.insert(0,'../tests_acceptance/W171')
import test_workbench as T
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.access_workbench import router as r
with tempfile.TemporaryDirectory() as tmp:
    app=create_app(Settings(data_dir=Path(tmp),seed_demo=False))
    with app.state.db.session() as s:put_doc(s,CaseRow,'CASE-A','CASE-A',{'caseId':'CASE-A','title':'CASE-A'})
    with TestClient(app,raise_server_exceptions=True) as c:
        T.save(c);orig=r.get_doc;once=[False]
        def raced(session,model,cid,key):
            res=orig(session,model,cid,key)
            if not once[0]:
                once[0]=True
                try:
                    with c.app.state.db.session() as other:
                        p=default_policy();p['version']='2.0.0';put_doc(other,AccessPolicyRow,'CASE-A','policy',p);T.event(other,command='version-2')
                except Exception as e:
                    print('CONCURRENT WRITER FAILED:',type(e).__name__,str(e).splitlines()[0]);raise
            return res
        r.get_doc=raced
        try:print(c.get(T.url()).status_code)
        except Exception as e:print('SERVER EXCEPTION:',type(e).__name__,str(e).splitlines()[0])
