import os,sys,pathlib,json,tempfile,base64,hashlib
from types import SimpleNamespace
R=pathlib.Path(os.environ["MCIS_PINNED_SOURCE"]);sys.path.insert(0,str(R/'service'))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from mcis_service.db import Base,Database,put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.evidence.models import CustodyEventRow
from mcis_service.evidence.router import router
from mcis_service.evidence_intake.router import router as intake
from mcis_service.working_records_archive import service as archive
from mcis_service.audit.models import AuditEventRow
from mcis_service.track_history.models import LocalReceipt
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy

def out(x):print(json.dumps(x),flush=True)
with tempfile.TemporaryDirectory(prefix='w17-receipts-') as d:
 db=Database('sqlite:///'+d+'/test.db');Base.metadata.create_all(db.engine)
 with db.session() as s:
  for case in ['SYN-A','SYN-B']:put_doc(s,CaseRow,case,case,{'caseId':case,'isFictionalDemo':True})
 app=FastAPI();app.state.db=db;app.state.settings=SimpleNamespace(blob_dir=pathlib.Path(d)/'blobs');app.include_router(router);app.include_router(intake)
 with TestClient(app) as c:
  h={'X-MCIS-Role':'LeadInvestigator','X-MCIS-Operator':'synthetic-reader'};registered={}
  for case in ['SYN-A','SYN-B']:
   body={'profile':'mcis-evidence-intake-v1','fileName':case+'.txt','contentBase64':base64.b64encode(('Invented opaque bytes '+case).encode()).decode(),'title':'SOURCE-'+case,'source':'Synthetic '+case,'extractedBy':'synthetic','extractedUtc':'2026-01-01T00:00:00Z','category':'Other','confidentiality':'Restricted','note':'Visible synthetic receipt test'}
   p=c.post('/api/v1/cases/'+case+'/evidence-intakes:preview',json=body,headers=h);assert p.status_code==200,p.text
   r=c.post('/api/v1/cases/'+case+'/evidence-intakes:commit',json={**body,'requestDigest':p.json()['requestDigest'],'confirmed':True},headers=h);assert r.status_code==200,r.text;registered[case]=r.json()
  out({'ready':True,'registered':registered})
  for line in sys.stdin:
   req=json.loads(line)
   if req=={'control':'denyB'}:
    policy=default_policy();policy['matrix']['LeadInvestigator']['evidence_meta']='Deny'
    with db.session() as s:put_doc(s,AccessPolicyRow,'SYN-B','policy',policy)
    out({'denied':True});continue
   path=req['path'];assert path.startswith('/api/v1/cases/SYN-');assert not any(x in path for x in ['/content','download',':preview',':commit'])
   response=c.get(path,headers={'X-MCIS-Role':req['role'],'X-MCIS-Operator':'synthetic-reader'})
   out({'path':path,'status':response.status_code,'bodyBase64':base64.b64encode(response.content).decode(),'sha256':hashlib.sha256(response.content).hexdigest()})
 with db.session() as s:
  events=list(s.scalars(select(CustodyEventRow)));assert len(events)==2 and all(e.kind=='Register' for e in events)
  assert len(list(s.scalars(select(AuditEventRow))))==2
 db.engine.dispose()
assert not pathlib.Path(d).exists()
