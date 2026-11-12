"""Independent synthetic working-archive helpers; no work occurs on import."""
import base64,hashlib,io,json,uuid,zipfile
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import text
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
CID='SYN-ARCHIVE-B';BASE='/api/v1/cases/'+CID;H={'X-MCIS-Role':'LeadInvestigator','X-MCIS-Operator':'Synthetic Archivist'};MEMBER='working-records/backup.v1.json'
def client(path):return TestClient(create_app(Settings(data_dir=Path(path),seed_demo=False)))
def seed(c):
 case={'caseId':CID,'schemaVersion':'1.0.0','title':'Synthetic working archive','accidentCode':'','accidentType':'Collision','accidentGrade':'','incidentTimeUtc':'2026-01-01T00:00:00Z','caseEpochUtc':'2026-01-01T00:00:00Z','displayTimeZoneOffsetMinutes':480,'incidentLocation':{'lonDeg':120,'latDeg':30,'heightM':0},'seaLevelOffsetM':0,'leadInvestigator':'Synthetic','agencyName':'Synthetic','isFictionalDemo':True,'summaryNotes':''}
 with c.app.state.db.session() as s:put_doc(s,CaseRow,CID,CID,case)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def unzip(raw):
 with zipfile.ZipFile(io.BytesIO(raw)) as z:return {n:z.read(n) for n in z.namelist()}
def export(c):
 r=c.get(BASE+'/export',headers=H);assert r.status_code==200,r.text;assert r.headers['cache-control']=='no-store';return r.content

def intake(c,raw,commit=False):
 body={'contentBase64':base64.b64encode(raw).decode()}
 if commit:body.update(confirmed=True,sourceSha256=sha(raw))
 return c.post('/api/v1/packages/intakes:'+('commit' if commit else 'preview'),headers=H,json=body)
def state(c):
 with c.app.state.db.session() as s:
  names=s.execute(text("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")).scalars().all()
  tables={n:s.execute(text(f'SELECT * FROM "{n}"')).all() for n in names}
 root=c.app.state.settings.blob_dir
 files={str(p.relative_to(root)):sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
 return tables,files

def create_evidence(c):
 raw='SYNTHETIC ONLY: 中文🚢原件\n'.encode()
 body={'profile':'mcis-evidence-intake-v1','fileName':'synthetic.txt','contentBase64':base64.b64encode(raw).decode(),'title':'Synthetic source','source':'Synthetic fixture','extractedBy':'Synthetic person','extractedUtc':'2026-01-01T00:00:00Z','category':'Testimony','confidentiality':'Restricted','note':'Not real evidence'}
 r=c.post(BASE+'/evidence-intakes:preview',headers=H,json=body);assert r.status_code==200,r.text
 commit={**body,'requestDigest':r.json()['requestDigest'],'confirmed':True}
 r=c.post(BASE+'/evidence-intakes:commit',headers=H,json=commit);assert r.status_code in (200,201),r.text
 return r.json()['evidenceId'],commit,raw

def populate(c):
 eid,evbody,raw=create_evidence(c)
 manual={'requestId':str(uuid.uuid4()),'backupAcknowledged':True,'interviewee':{'intervieweeId':'SYN-P','name':'Synthetic Person','role':'Witness','affiliation':'Synthetic'},'startUtc':'2026-01-01T00:00:00Z','sourceEvidenceId':eid}
 r=c.post(BASE+'/manual-interviews',headers=H,json=manual);assert r.status_code==201,r.text;rid=r.json()['receipt']['recordId']
 turns=[]
 for index in range(2):
  r=c.get(BASE+'/manual-interviews/'+rid,headers=H);assert r.status_code==200,r.text
  b={'requestId':str(uuid.uuid4()),'backupAcknowledged':True,'expectedDigest':r.json()['documentDigest'],'question':f' 原问题{index} 🚢\n','answer':f' 原回答{index} 中文\n','sensitiveFragments':[]}
  r=c.post(BASE+'/manual-interviews/'+rid+'/turns',headers=H,json=b);assert r.status_code==201,r.text;turns.append(b)
 # A legitimate old writer makes the current doc differ from the last receipt digest.
 r=c.post(BASE+'/interviews/'+rid+'/turns',headers=H,json={'question':'Synthetic legacy question','answer':'Synthetic legacy answer'});assert r.status_code==201,r.text
 r=c.post(BASE+'/reports',headers=H,json={'templateId':'imo-cic','lang':'zh'});assert r.status_code==201,r.text;report=r.json();rpt=report['reportId'];section=report['sections'][0]['sectionId']
 r=c.patch(BASE+'/reports/'+rpt+'/sections/'+section,headers=H,json={'action':'confirm','reason':'Synthetic review only'});assert r.status_code==200,r.text
 r=c.post(BASE+'/reports/'+rpt+':generate',headers=H,json={'templateId':'imo-cic','lang':'zh'});assert r.status_code==201,r.text
 return {'evidenceId':eid,'evidenceBody':evbody,'raw':raw,'recordId':rid,'manualBody':manual,'turnBodies':turns,'reportId':rpt}

def archive(raw):return json.loads(unzip(raw)[MEMBER])
def originals_equal(a,b):
 for key in ('interviews','reports','reportSnapshots','manualReceipts'):assert b[key]==a[key],key

def inert(c,fixture):
 rid=fixture['recordId'];digest=fixture['evidenceBody']['requestDigest']
 for r in [c.post(BASE+'/manual-interviews',headers=H,json=fixture['manualBody']),c.post(BASE+'/manual-interviews/'+rid+'/turns',headers=H,json=fixture['turnBodies'][0]),c.get(BASE+'/manual-interviews/requests/'+fixture['manualBody']['requestId'],headers=H),c.get(BASE+'/evidence/'+fixture['evidenceId']+'/intake',headers=H),c.get(BASE+'/evidence-intakes/'+digest,headers=H),c.post(BASE+'/evidence-intakes:commit',headers=H,json=fixture['evidenceBody']),c.get(BASE+'/evidence/'+fixture['evidenceId']+'/content',headers=H)]:
  assert r.status_code==409,r.text
  assert r.headers['cache-control']=='no-store'
