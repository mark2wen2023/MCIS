"""Acceptance-only localhost process. Real app, HTTP, SQLite, renderer; no OCR."""
import argparse,base64,hashlib,importlib.util,json,io,socket,subprocess,sys,tempfile,threading,time,urllib.request
from pathlib import Path
P=argparse.ArgumentParser();P.add_argument('--repo',type=Path,required=True);P.add_argument('--browser',action='store_true');P.add_argument('--playwright-module');P.add_argument('--chromium',default='/usr/bin/chromium');args=P.parse_args()
HERE=Path(__file__).resolve().parent;root=args.repo.resolve()
pins=json.loads((HERE/'pins.json').read_text())
for rel,sha in pins['blobs'].items():
 raw=(root/rel).read_bytes()
 if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=sha:raise SystemExit('Fixed source mismatch: '+rel)
sys.path.insert(0,str(root/'service'))
import uvicorn
from mcis_service.config import Settings
from mcis_service.image_review.app import create_image_review_app,Record
from mcis_service.image_review.synthetic_pdf import SyntheticPdfBinding,CASE,SOURCE,renderer
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.evidence.models import CustodyEventRow
spec=importlib.util.spec_from_file_location('fixed_fixture',root/'tests_acceptance/pdf-page-derivation/check.py');fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(b):return base64.b64encode(b).decode()
result={'fixedCommit':pins['commit'],'browser':'not_run','http':'not_run'}
with tempfile.TemporaryDirectory(prefix='w4-browser-synthetic-') as tmp:
 app=create_image_review_app(Settings(data_dir=Path(tmp),seed_demo=False))
 try:
  with app.state.db.session() as s:
   assert s.query(CaseRow).count()==0
   put_doc(s,CaseRow,CASE,CASE,dict(caseId=CASE,schemaVersion='1.0.0',title='Synthetic PDF pages',accidentType='Synthetic',isFictionalDemo=True,caseEpochUtc='2026-02-01T12:00:00Z',incidentTimeUtc='2026-02-01T12:00:00Z',incidentLocation=dict(lonDeg=-130,latDeg=-30),displayTimeZoneOffsetMinutes=0))
   put_doc(s,AccessPolicyRow,CASE,'policy',default_policy())
  sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(128)
  port=sock.getsockname()[1];origin='http://127.0.0.1:'+str(port)
  server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='error',access_log=False))
  thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
  def request(path,body=None):
   data=None if body is None else json.dumps(body).encode()
   req=urllib.request.Request(origin+path,data=data,headers={'Content-Type':'application/json','X-MCIS-Role':'Investigator','X-MCIS-Operator':'Synthetic acceptance'})
   with urllib.request.urlopen(req,timeout=20) as r:return r.status,r.headers,r.read()
  try:
   for _ in range(100):
    if server.started:break
    if not thread.is_alive():raise RuntimeError('server exited before ready')
    time.sleep(.05)
   assert server.started
   assert request('/api/v1/health')[0]==200
   pdf=fixture.synthetic_pdf();assert sha(pdf)==SOURCE
   desc,derived_image=renderer().render(pdf,expected_sha256=SOURCE,physical_page=1)
   _,image=renderer().render(pdf,expected_sha256=SOURCE,physical_page=2)
   assert sha(image)!=sha(derived_image) # visible blue registered control vs red derived page 1
   raw=b'SYNTHETIC supplied recognizer bytes; no OCR executed'
   candidate=dict(schema='mcis.offline-ocr-candidate/v0.1',production_import_supported=False,page_index_inferred=False,limitations=['synthetic supplied OCR; image/PDF mapping not verified'],confirmed=False,needs_review=True,status='pending_human_review',
    source=dict(pdf_sha256=sha(pdf),image_sha256=sha(image),raw_sha256=sha(raw),pdf_page_1based=1,printed_page='',mapping_basis='deliberately different blue page-2 control; not page-1 lineage',width=256,height=256),
    recognizer=dict(paddlepaddle='synthetic',paddleocr='synthetic',paddlex='synthetic',pipeline='synthetic',models=['fixture'],device='none'),raw_page_index=None,coordinate_space='rendered_page_pixels_xy_top_left',tables=[],
    text_lines=[dict(line_index=0,text='SYNTHETIC LINE',is_blank=False,confirmed=False,needs_review=True,model_score=.5,bbox=[0,0,2,1],polygon=[[0,0],[2,0],[2,1],[0,1]])])
   base='/api/v1/cases/'+CASE
   records={}
   for name,data in {'pdf':pdf,'image':image,'raw':raw,'candidate':json.dumps(candidate).encode()}.items():
    body=dict(profile='mcis-evidence-intake-v1',fileName=name+'.bin',title='Synthetic '+name,source='fixed fixture',extractedBy='Synthetic author',extractedUtc='2026-02-01T00:00:00Z',category='Document',confidentiality='Restricted',note='synthetic only',contentBase64=enc(data))
    preview=json.loads(request(base+'/evidence-intakes:preview',body)[2])
    records[name]=json.loads(request(base+'/evidence-intakes:commit',{**body,'requestDigest':preview['requestDigest'],'confirmed':True})[2])
   review=json.loads(request(base+'/image-reviews',{'bindings':{k:v['requestDigest'] for k,v in records.items()},'acknowledgeArchiveBlocked':True})[2])
   run=review['runId'];app.state.synthetic_pdf_binding=SyntheticPdfBinding(run,0,records['pdf']['requestDigest'],records['pdf']['evidenceId'])
   def counts():
    with app.state.db.session() as s:return (s.query(CustodyEventRow).filter(CustodyEventRow.kind=='Access').count(),s.query(Record).count())
   before=counts();assert before==(0,1)
   html=request('/image-review-lab')[2];assert b'id="show-pdf" hidden' not in html
   assert request('/image-review-lab/pdf-host.js')[0]==200
   if args.browser:
    if not args.playwright_module:raise ValueError('--playwright-module required')
    proc=subprocess.run(['node',str(HERE/'browser.cjs'),args.playwright_module,args.chromium,origin,CASE,run,base+'/evidence-intakes/'+records['image']['requestDigest']+':download',sha(image)],capture_output=True,text=True,timeout=60)
    if proc.returncode:
     result.update(http='startup_registration_page_passed',browser='blocked_or_failed',browserExit=proc.returncode,browserStage=json.loads(proc.stdout).get('stage','unknown') if proc.stdout.strip() else 'no_receipt')
     print(json.dumps(result));raise SystemExit(2)
    browser=json.loads(proc.stdout);assert browser['passed']
    assert counts()==(2,1) # one PDF derived Access plus one explicit registered PNG Access
    result.update(http='passed',browser=browser)
   else:
    status,headers,body=request(base+'/image-reviews/'+run+'/synthetic-pdf-page',{'expectedRevision':0})
    d=json.loads(body);assert status==200 and headers['Cache-Control']=='no-store'
    assert set(d)=={'caseId','runId','revision','description','pngBase64'}
    assert (d['caseId'],d['runId'],d['revision'])==(CASE,run,0)
    assert d['description']==desc and base64.b64decode(d['pngBase64'])==derived_image
    assert b'%PDF-' not in body and 'registration_digest' not in d
    assert counts()==(1,1)
    from PIL import Image
    with Image.open(io.BytesIO(derived_image)) as im:assert im.convert('RGB').getpixel((128,128))==(255,0,0)
    status,headers,png=request(base+'/evidence-intakes/'+records['image']['requestDigest']+':download',{'purpose':'Synthetic distinct PNG restoration control'})
    assert status==200 and png==image and headers['X-Sha256']==sha(image)
    with Image.open(io.BytesIO(png)) as im:assert im.convert('RGB').getpixel((128,128))==(0,0,255)
    assert counts()==(2,1)
    result.update(http='passed',derivedAccessDelta=1,registeredImageAccessDelta=1,distinctPixels=True,ocrReviewRowsUnchanged=True)
   with app.state.db.session() as s:assert [r.key for r in s.query(CaseRow)]==[CASE]
   print(json.dumps(result))
  finally:
   server.should_exit=True;thread.join(timeout=10);sock.close()
   if thread.is_alive():raise RuntimeError('server failed to stop')
 finally:app.state.db.engine.dispose()
