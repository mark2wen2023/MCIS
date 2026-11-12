"""Independent synthetic track-history fixtures, no work on import."""
import base64,hashlib,io,json,zipfile
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import text
from mcis_service.main import create_app
from mcis_service.config import Settings
CID='SYN-TRACK-HISTORY';BASE='/api/v1/cases/'+CID;URL=BASE+'/track-imports';H={'X-MCIS-Role':'LeadInvestigator','X-MCIS-Operator':'Synthetic Track Reviewer'}
CSV=b'utc,latDeg,lonDeg,sogKn,sogStatus,cogDeg,cogStatus,hdgDeg,hdgStatus\r\n2026-01-01T00:00:01Z,31,121,8,reported,20,reported,20,reported\r\n2026-01-01T00:00:02Z,31.001,121.001,8,reported,21,reported,21,reported\r\n'
def sha(x):return hashlib.sha256(x).hexdigest()
def client(path):return TestClient(create_app(Settings(data_dir=Path(path),seed_demo=False)),raise_server_exceptions=False)
def seed(c):
 d={'caseId':CID,'schemaVersion':'1.0.0','title':'Synthetic track history only','accidentType':'Collision','incidentTimeUtc':'2026-01-01T00:00:00Z','caseEpochUtc':'2026-01-01T00:00:00Z','displayTimeZoneOffsetMinutes':0,'incidentLocation':{'lonDeg':121,'latDeg':31,'heightM':0},'seaLevelOffsetM':0,'isFictionalDemo':True}
 r=c.post('/api/v1/cases',json=d,headers=H);assert r.status_code==201,r.text
 vessel(c,'ship')
def vessel(c,id):
 r=c.post(BASE+'/vessels',json={'caseId':CID,'vesselId':id,'name':'Synthetic '+id},headers=H);assert r.status_code==201,r.text

def body(v='ship',csv=CSV):return {'profile':'mcis-utc-v1','vesselId':v,'fileName':'synthetic.csv','source':'Synthetic source only','timeBasis':'Synthetic UTC not real observation','contentBase64':base64.b64encode(csv).decode()}
def prepared(c,b=None):
 b=b or body();r=c.post(URL+':preview',json=b,headers=H);assert r.status_code==200 and r.json()['canCommit'],r.text
 return {**b,'previewDigest':r.json()['previewDigest'],'confirmed':True}
def commit(c,b):return c.post(URL+':commit',json=b,headers=H)
def populate(c):
 seed(c);b=prepared(c);r=commit(c,b);assert r.status_code==200,r.text
 d=r.json();report=c.get(URL+'/'+d['previewDigest']+'/report',headers=H);assert report.status_code==200,report.text
 return b,d,report.content

def export(c):
 r=c.get(BASE+'/export',headers=H);assert r.status_code==200,r.text;return r.content
def intake(c,raw,commit=False):
 b={'contentBase64':base64.b64encode(raw).decode()}
 if commit:b.update(confirmed=True,sourceSha256=sha(raw))
 return c.post('/api/v1/packages/intakes:'+('commit' if commit else 'preview'),json=b,headers=H)
def unzip(b):
 with zipfile.ZipFile(io.BytesIO(b)) as z:return {n:z.read(n) for n in z.namelist()}
def pack(files):
 out=io.BytesIO()
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in files.items():z.writestr(n,b)
 return out.getvalue()
def downgrade(raw,version):
 files=unzip(raw);d=json.loads(files['manifest.json']);d['packageVersion']=version;files['manifest.json']=json.dumps(d).encode();return pack(files)
def state(c):
 with c.app.state.db.engine.connect() as db:
  names=sorted(db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'" )).scalars())
  tables={n:[tuple(row) for row in db.execute(text('SELECT * FROM "'+n+'"'))] for n in names}
 root=c.app.state.settings.blob_dir
 files={str(p.relative_to(root)):sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
 return tables,files

def process_commit(path,b,ready,go,out):
 try:
  with client(path) as c:
   ready.set()
   if not go.wait(20):raise RuntimeError('parent did not release process')
   r=commit(c,b);out.put({'status':r.status_code,'body':r.json()})
 except Exception as e:out.put({'error':type(e).__name__+': '+str(e)})
