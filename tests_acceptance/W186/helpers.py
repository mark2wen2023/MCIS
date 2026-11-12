"""Rebuilt independent synthetic helpers. No actions or tests run on import."""
import base64,hashlib,io,json,uuid,zipfile
from pathlib import Path
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
CID='SYN-W186'
def client(path):return TestClient(create_app(Settings(data_dir=Path(path),seed_demo=False)))
def seed(c):
 case={'caseId':CID,'schemaVersion':'1.0.0','title':'合成备份验收','accidentCode':'','accidentType':'Collision','accidentGrade':'','incidentTimeUtc':'2026-01-01T00:00:00Z','caseEpochUtc':'2026-01-01T00:00:00Z','displayTimeZoneOffsetMinutes':480,'incidentLocation':{'lonDeg':120,'latDeg':30,'heightM':0},'seaLevelOffsetM':0,'leadInvestigator':'Synthetic','agencyName':'Synthetic','isFictionalDemo':True,'summaryNotes':''}
 with c.app.state.db.session() as s:put_doc(s,CaseRow,CID,CID,case)
def save_body(digest=None,index=1):return {'requestId':str(uuid.uuid4()),'expectedDigest':digest,'draft':{'scope':'合成工作情境','entries':[{'id':'entry','categoryCode':'UA-ERR-DEC','description':f'人工假设{index}','rationale':'尚未专业核实 🛳'}]},'expectedSources':[]}
def endpoint(action):return f'/api/v1/cases/{CID}/human-factors/hfacs:{action}'
def save(c,b):
 r=c.post(endpoint('save'),json=b);assert r.status_code==200,r.text
 return r.json()['document']
def unzip(raw):
 with zipfile.ZipFile(io.BytesIO(raw)) as z:return {n:z.read(n) for n in z.namelist()}
def repack(files):
 m=json.loads(files['manifest.json'])
 for item in m['files']:
  raw=files[item['relativePath']];item['sha256']=hashlib.sha256(raw).hexdigest();item['sizeBytes']=len(raw)
 files={**files,'manifest.json':json.dumps(m,ensure_ascii=False).encode()};buf=io.BytesIO()
 with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in files.items():z.writestr(n,b)
 return buf.getvalue()
def intake(c,raw,commit=False):
 body={'contentBase64':base64.b64encode(raw).decode()}
 if commit:body.update(confirmed=True,sourceSha256=hashlib.sha256(raw).hexdigest())
 return c.post('/api/v1/packages/intakes:'+('commit' if commit else 'preview'),json=body)
def export(c):
 r=c.get(f'/api/v1/cases/{CID}/export');assert r.status_code==200,r.text
 return r.content
