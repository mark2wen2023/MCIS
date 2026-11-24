import os,sys,json,tempfile,base64,hashlib
from pathlib import Path
root=Path(os.environ["MCIS_PINNED_SOURCE"])
for p,h in json.loads((root/'pins.json').read_text()).items():
 b=(root/p).read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==h
sys.path.insert(0,str(root/'service'))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mcis_service.db import Base,Database,put_doc
from mcis_service.cases.router import router as cases
from mcis_service.environment.router import router as environment
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
CASE='synthetic-case'
records=[{'caseId':CASE,'observationId':'A','sourceLabel':'合成 A','description':'独立记录 A','valueOrigin':'Direct','locationDescription':'河段 A','observedAtUtc':'2026-01-01T00:00:00Z','currentSpeedKn':0,'currentToDirDeg':90},{'caseId':CASE,'observationId':'B','sourceLabel':'合成 B','description':'独立记录 B','valueOrigin':'Estimated','locationDescription':'河段 B','observedAtUtc':'2026-01-01T00:00:00Z','currentSpeedKn':None,'currentToDirDeg':270}]
def out(x):print(json.dumps(x,ensure_ascii=False),flush=True)
with tempfile.TemporaryDirectory(prefix='w9-joined-') as directory:
 db=Database('sqlite:///'+directory+'/test.db')
 try:
  Base.metadata.create_all(db.engine);app=FastAPI();app.state.db=db;app.include_router(cases);app.include_router(environment)
  with TestClient(app) as c:
   h={'X-MCIS-Role':'Investigator','X-MCIS-Operator':'synthetic-host'}
   doc={'caseId':CASE,'schemaVersion':'1.0.0','title':'虚构环境验收','accidentType':'Collision','caseEpochUtc':'2026-01-01T00:00:00Z','incidentTimeUtc':'2026-01-01T00:00:00Z','incidentLocation':{'lonDeg':0,'latDeg':0},'displayTimeZoneOffsetMinutes':0,'isFictionalDemo':True}
   r=c.post('/api/v1/cases',json=doc,headers=h);assert r.status_code==201,r.text
   path='/api/v1/cases/'+CASE+'/environment-observations'
   for record in records:
    r=c.post(path,json=record,headers=h);assert r.status_code==201,r.text
   out({'ready':True,'records':2,'caseId':CASE})
   for line in sys.stdin:
    req=json.loads(line)
    if req=={'control':'deny'}:
     policy=default_policy();policy['matrix']['Public']['ais_sim']='Deny'
     with db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',policy)
     out({'denied':True});continue
    assert set(req)=={'path','role'} and req['role']=='Public'
    assert req['path'] in ['/api/v1/cases/'+x+y for x in [CASE,'synthetic-missing'] for y in ['', '/environment-observations']]
    r=c.get(req['path'],headers={'X-MCIS-Role':'Public','X-MCIS-Operator':'synthetic-reader'})
    if r.status_code!=200:assert '独立记录' not in r.text and '合成 A' not in r.text
    if req['path']==path and r.status_code==200:assert r.json()==records
    out({'path':req['path'],'status':r.status_code,'bodyBase64':base64.b64encode(r.content).decode(),'sha256':hashlib.sha256(r.content).hexdigest()})
 finally:db.engine.dispose()
assert not Path(directory).exists()
