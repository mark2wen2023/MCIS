"""W4 extended harness (outside repo tree, does NOT modify repo). Mirrors run.py setup exactly,
keeps the synthetic SQLite on disk for direct inspection, adds a server-side delay switch
(ASGI wrapper reading a control file) so old responses can be delayed without browser mocks.
Usage: harness.py --repo R --data D --viewport WxH --pw PW --chromium C --shots S --tag T"""
import argparse,asyncio,base64,hashlib,importlib.util,json,os,socket,sqlite3,subprocess,sys,threading,time,urllib.request
from pathlib import Path
P=argparse.ArgumentParser()
for a in ['--repo','--data','--viewport','--pw','--chromium','--shots','--tag']:P.add_argument(a,required=True)
args=P.parse_args();root=Path(args.repo).resolve();data=Path(args.data);data.mkdir(parents=True,exist_ok=False)
HERE=Path(__file__).resolve().parent;DELAY=data/'delay.json'
sys.path.insert(0,str(root/'service'))
import uvicorn
from mcis_service.config import Settings
from mcis_service.image_review.app import create_image_review_app
from mcis_service.image_review.synthetic_pdf import SyntheticPdfBinding,CASE,SOURCE,renderer
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
spec=importlib.util.spec_from_file_location('fixed_fixture',root/'tests_acceptance/pdf-page-derivation/check.py');fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
sha=lambda b:hashlib.sha256(b).hexdigest();enc=lambda b:base64.b64encode(b).decode()
app=create_image_review_app(Settings(data_dir=data,seed_demo=False))
class Delay:
 def __init__(s,inner):s.inner=inner
 async def __call__(s,scope,receive,send):
  if scope['type']=='http' and DELAY.exists():
   rule=json.loads(DELAY.read_text())
   if scope['path'].endswith(rule['suffix']) and rule.get('remaining',0)>0:
    rule['remaining']-=1;DELAY.write_text(json.dumps(rule))
    # Delay the *response* after the real handler has run (handler/audit executes first).
    async def late_send(m,_send=send):
     if m['type']=='http.response.start':await asyncio.sleep(rule['seconds'])
     await _send(m)
    return await s.inner(scope,receive,late_send)
  return await s.inner(scope,receive,send)
with app.state.db.session() as s:
 put_doc(s,CaseRow,CASE,CASE,dict(caseId=CASE,schemaVersion='1.0.0',title='Synthetic PDF pages',accidentType='Synthetic',isFictionalDemo=True,caseEpochUtc='2026-02-01T12:00:00Z',incidentTimeUtc='2026-02-01T12:00:00Z',incidentLocation=dict(lonDeg=-130,latDeg=-30),displayTimeZoneOffsetMinutes=0))
 put_doc(s,AccessPolicyRow,CASE,'policy',default_policy())
sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(128);port=sock.getsockname()[1];origin='http://127.0.0.1:'+str(port)
server=uvicorn.Server(uvicorn.Config(Delay(app),host='127.0.0.1',port=port,log_level='warning',access_log=True))
thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
def request(path,body=None):
 req=urllib.request.Request(origin+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json','X-MCIS-Role':'Investigator','X-MCIS-Operator':'Synthetic acceptance'})
 with urllib.request.urlopen(req,timeout=20) as r:return r.status,r.headers,r.read()
for _ in range(100):
 if server.started:break
 time.sleep(.05)
assert server.started and request('/api/v1/health')[0]==200
pdf=fixture.synthetic_pdf();assert sha(pdf)==SOURCE
_,red=renderer().render(pdf,expected_sha256=SOURCE,physical_page=1)
_,image=renderer().render(pdf,expected_sha256=SOURCE,physical_page=2)
raw=b'SYNTHETIC supplied recognizer bytes; no OCR executed'
candidate=dict(schema='mcis.offline-ocr-candidate/v0.1',production_import_supported=False,page_index_inferred=False,limitations=['synthetic supplied OCR; image/PDF mapping not verified'],confirmed=False,needs_review=True,status='pending_human_review',
 source=dict(pdf_sha256=sha(pdf),image_sha256=sha(image),raw_sha256=sha(raw),pdf_page_1based=1,printed_page='',mapping_basis='deliberately different blue page-2 control; not page-1 lineage',width=256,height=256),
 recognizer=dict(paddlepaddle='synthetic',paddleocr='synthetic',paddlex='synthetic',pipeline='synthetic',models=['fixture'],device='none'),raw_page_index=None,coordinate_space='rendered_page_pixels_xy_top_left',tables=[],
 text_lines=[dict(line_index=0,text='SYNTHETIC LINE',is_blank=False,confirmed=False,needs_review=True,model_score=.5,bbox=[0,0,2,1],polygon=[[0,0],[2,0],[2,1],[0,1]])])
base='/api/v1/cases/'+CASE;records={}
for name,d in {'pdf':pdf,'image':image,'raw':raw,'candidate':json.dumps(candidate).encode()}.items():
 body=dict(profile='mcis-evidence-intake-v1',fileName=name+'.bin',title='Synthetic '+name,source='fixed fixture',extractedBy='Synthetic author',extractedUtc='2026-02-01T00:00:00Z',category='Document',confidentiality='Restricted',note='synthetic only',contentBase64=enc(d))
 pv=json.loads(request(base+'/evidence-intakes:preview',body)[2])
 records[name]=json.loads(request(base+'/evidence-intakes:commit',{**body,'requestDigest':pv['requestDigest'],'confirmed':True})[2])
bindings={k:v['requestDigest'] for k,v in records.items()}
runA=json.loads(request(base+'/image-reviews',{'bindings':bindings,'acknowledgeArchiveBlocked':True})[2])['runId']
try:runB=json.loads(request(base+'/image-reviews',{'bindings':bindings,'acknowledgeArchiveBlocked':True})[2])['runId']
except Exception as e:runB=None;print('second run not creatable:',repr(e),file=sys.stderr)
app.state.synthetic_pdf_binding=SyntheticPdfBinding(runA,0,records['pdf']['requestDigest'],records['pdf']['evidenceId'])
db=data/'mcis.db'
cfg=dict(origin=origin,caseId=CASE,runA=runA,runB=runB,imagePath=base+'/evidence-intakes/'+records['image']['requestDigest']+':download',imageSha=sha(image),redSha=sha(red),
 db=str(db),delayFile=str(DELAY),viewport=args.viewport,shots=args.shots,tag=args.tag,pdfEvidenceId=records['pdf']['evidenceId'],imageEvidenceId=records['image']['evidenceId'])
(data/'cfg.json').write_text(json.dumps(cfg,indent=1))
proc=subprocess.run(['node',str(HERE/'driver.cjs'),args.pw,args.chromium,str(data/'cfg.json')],capture_output=True,text=True,timeout=300)
sys.stderr.write(proc.stderr)
server.should_exit=True;thread.join(timeout=10);sock.close();app.state.db.engine.dispose()
con=sqlite3.connect(db)
rows=con.execute("select seq,evidence_id,kind,utc,detail from custody_events where case_id=? order by seq",(CASE,)).fetchall()
summary=dict(driverExit=proc.returncode,driver=json.loads(proc.stdout.strip().splitlines()[-1]) if proc.stdout.strip() else None,
 sqliteAccessTotal=sum(1 for r in rows if r[2]=='Access'),
 sqliteAccessPdf=sum(1 for r in rows if r[2]=='Access' and r[1]==cfg['pdfEvidenceId']),
 sqliteAccessImage=sum(1 for r in rows if r[2]=='Access' and r[1]==cfg['imageEvidenceId']),
 custodyRows=[list(r) for r in rows])
print(json.dumps(summary,ensure_ascii=False,indent=1))
sys.exit(0 if proc.returncode==0 else 3)
