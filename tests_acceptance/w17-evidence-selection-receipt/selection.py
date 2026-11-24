import os,sys,pathlib,json,tempfile,base64,hashlib
R=pathlib.Path(os.environ["MCIS_PINNED_SOURCE"]);sys.path.insert(0,str(R/'service'))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from mcis_service.db import Base,Database,put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.evidence.models import EvidenceRow,CustodyEventRow
from mcis_service.evidence.router import router
from mcis_service.evidence.service import append_custody
from mcis_service.audit.models import AuditEventRow

def out(x):print(json.dumps(x),flush=True)
with tempfile.TemporaryDirectory(prefix='w17-lists-') as d:
 db=Database('sqlite:///'+d+'/test.db');Base.metadata.create_all(db.engine)
 with db.session() as s:
  for case in ['SYN-A','SYN-B']:
   put_doc(s,CaseRow,case,case,{'caseId':case,'isFictionalDemo':True})
   item={'caseId':case,'evidenceId':'EV-001','title':'SOURCE-'+case,'source':'Synthetic '+case,'extractedBy':'synthetic','extractedUtc':'2026-01-01T00:00:00Z','sha256':hashlib.sha256(case.encode()).hexdigest(),'relativePath':'','category':'Other','confidentiality':'Restricted','note':'Synthetic metadata only; no original bytes'}
   put_doc(s,EvidenceRow,case,'EV-001',item);append_custody(s,case_id=case,evidence_id='EV-001',kind='Register',operator='synthetic',role='LeadInvestigator',sha256=item['sha256'],detail='synthetic setup',item=item)
 app=FastAPI();app.state.db=db;app.include_router(router)
 with TestClient(app) as c:
  out({'ready':True})
  for line in sys.stdin:
   req=json.loads(line);path=req['path'];assert path.startswith('/api/v1/cases/SYN-');assert not any(x in path for x in ['/content','download','intake'])
   response=c.get(path,headers={'X-MCIS-Role':req['role'],'X-MCIS-Operator':'synthetic-reader'})
   out({'path':path,'status':response.status_code,'bodyBase64':base64.b64encode(response.content).decode(),'sha256':hashlib.sha256(response.content).hexdigest()})
 with db.session() as s:
  assert len(list(s.scalars(select(CustodyEventRow))))==2
  assert len(list(s.scalars(select(AuditEventRow))))==2
 db.engine.dispose()
assert not pathlib.Path(d).exists()
