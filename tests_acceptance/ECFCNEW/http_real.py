"""Independent true loopback HTTP/core/SQLite check; does not substitute for browser QA."""
import os,socket,subprocess,tempfile,time,json,urllib.request,urllib.error,sqlite3,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent;A='INDEPENDENT-BROWSER-A';checks=[]
def check(v,label):assert v,label;checks.append(label)
with tempfile.TemporaryDirectory(prefix='ecfc-independent-http-')as tmp:
 listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(128);port=listener.getsockname()[1]
 env={**os.environ,'PYTHONPATH':str(ROOT/'service'),'ECFC_ACCEPTANCE_DATA':tmp,'ECFC_ACCEPTANCE_FD':str(listener.fileno())}
 p=subprocess.Popen([str(ROOT/'service/.venv/bin/python'),str(HERE/'server.py')],env=env,pass_fds=(listener.fileno(),),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);listener.close()
 def request(path,body=None,role='LeadInvestigator'):
  req=urllib.request.Request(f'http://127.0.0.1:{port}/api/v1/'+path,data=json.dumps(body).encode()if body is not None else None,headers={'X-MCIS-Role':role,'X-MCIS-Operator':'Independent Network','Content-Type':'application/json'})
  try:
   with urllib.request.urlopen(req,timeout=30)as r:return r.status,json.load(r),r.headers
  except urllib.error.HTTPError as r:return r.code,json.load(r),r.headers
 def counts():
  with sqlite3.connect(Path(tmp)/'mcis.db')as s:return tuple(s.execute('select count(*) from '+t).fetchone()[0]for t in ('ecfc_drafts','ecfc_draft_audit','ecfc_draft_requests'))
 try:
  for _ in range(200):
   assert p.poll()is None
   try:request('health');break
   except Exception:time.sleep(.05)
  else:raise RuntimeError('service unavailable')
  base=f'cases/{A}/ecfc/'
  status,ctx,h=request(base+'context');check(status==200 and ctx['archiveSupported']is False and h['cache-control']=='no-store','real context explicit archive boundary')
  src=ctx['sources'][0];draft={'scope':'Independent real HTTP synthetic hypothesis','nodes':[{'id':'event','kind':'Event','text':'Synthetic vessel turns','timeSeconds':None,'lane':0,'isPrimaryIncident':False,'evidenceIds':[src['evidenceId']]}],'edges':[]}
  status,pv,h=request(base+'preview',{'draft':draft,'expectedSources':[src]});check(status==200 and pv['persisted']is False and counts()==(0,0,0),'real preview core zero writes')
  b={'requestId':str(uuid.uuid4()),'expectedDigest':None,'draft':draft,'expectedSources':[src],'acknowledgeArchiveLimitation':True}
  missing=dict(b);missing.pop('acknowledgeArchiveLimitation');check(request(base+'save',missing)[0]==422 and counts()==(0,0,0),'real HTTP mandatory archive acknowledgement')
  status,one,h=request(base+'save',b);check(status==200 and one['document']['revision']==1 and counts()==(1,1,1),'real HTTP save one revision')
  check(request(base+'save',b)[1]==one and counts()==(1,1,1),'real HTTP same body receipt replay')
  check(request(base+'draft')[1]==one,'real HTTP reopen exact document')
  other={**b,'requestId':str(uuid.uuid4())};check(request(base+'save',other)[0]==409 and counts()==(1,1,1),'real HTTP optimistic conflict')
  status,data,h=request(f'cases/{A}/export');check(status==409 and data['code']=='ECFC_ARCHIVE_UNSUPPORTED','real HTTP refuses incomplete whole-case archive')
  check(request(base+'draft',role='Investigator')[0]==403,'real HTTP default investigator raw denial')
  status,a,h=request(base+'audit');check(status==200 and len(a['events'])==1 and a['events'][0]['requestId']==b['requestId'],'real HTTP audit binding')
  print(json.dumps({'passed':len(checks),'checks':checks,'finalCounts':counts()},ensure_ascii=False))
 finally:
  if p.poll()is None:p.terminate()
  try:p.wait(timeout=10)
  except subprocess.TimeoutExpired:p.kill();p.wait()
