"""Hands-on HTTP + SQLite probe of W17.1 against a real uvicorn on 127.0.0.1 (synthetic data, temp dir)."""
import json,os,socket,sqlite3,sys,tempfile,threading,time,urllib.request,urllib.error
from pathlib import Path
sys.path.insert(0,'.')
import uvicorn
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.audit import service as audit
from mcis_service.access_workbench import router as R
out={}
with tempfile.TemporaryDirectory(prefix='w17-probe-') as tmp:
 app=create_app(Settings(data_dir=Path(tmp),seed_demo=False))
 with app.state.db.session() as s:
  for cid in ('CASE-A','CASE-B'):put_doc(s,CaseRow,cid,cid,{'caseId':cid,'title':cid})
  p=default_policy();p['version']='1.0.0';put_doc(s,AccessPolicyRow,'CASE-A','policy',p)
 sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(64);port=sock.getsockname()[1]
 srv=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='error'));th=threading.Thread(target=lambda:srv.run(sockets=[sock]),daemon=True);th.start()
 while not srv.started:time.sleep(.05)
 def get(cid,role='Investigator'):
  req=urllib.request.Request(f'http://127.0.0.1:{port}/api/v1/cases/{cid}/access-workbench',headers={'X-MCIS-Role':role,'X-MCIS-Operator':'Synthetic probe'})
  try:
   with urllib.request.urlopen(req,timeout=30) as r:return r.status,dict(r.headers),json.loads(r.read())
  except urllib.error.HTTPError as e:return e.code,dict(e.headers),json.loads(e.read() or b'{}')
 db=Path(tmp)/'mcis.db'
 def rows():
  c=sqlite3.connect(f'file:{db}?mode=ro',uri=True);r={t:c.execute(f'select count(*) from {t}').fetchone()[0] for t in ('audit_events','access_policies' if False else 'audit_events')};c.close();return r
 before=rows()
 res={}
 for role in ['LeadInvestigator','Investigator','Public','ExternalExpert','InterestedState','AgentService']:
  for cid in ['CASE-A','CASE-B','NO-SUCH-CASE']:
   st,h,b=get(cid,role);res[f'{role}/{cid}']=dict(status=st,cacheControl=h.get('cache-control') or h.get('Cache-Control'),policySource=b.get('policySource'),version=(b.get('policy') or {}).get('version'),readOnly=b.get('readOnly'),identityMode=b.get('identityMode'),code=b.get('code'))
 out['roleMatrix']=res;out['auditRowsBeforeAfterGETs']=[before,rows()]
 # Real cross-thread concurrency: slow the endpoint's policy read, writer in another thread.
 orig=R.get_doc;ev=threading.Event()
 def slow(session,model,cid,key):
  r=orig(session,model,cid,key);ev.set();time.sleep(1.0);return r
 R.get_doc=slow;wres={}
 def writer():
  ev.wait();t0=time.time()
  try:
   with app.state.db.session() as o:
    p=default_policy();p['version']='2.0.0';put_doc(o,AccessPolicyRow,'CASE-A','policy',p)
    audit.append(o,case_id='CASE-A',operator='probe',role='LeadInvestigator',action='policy.update',category='Access',command='version-2',entity_type='accessPolicy',entity_id='policy')
   wres.update(ok=True,waitedSec=round(time.time()-t0,2))
  except Exception as e:wres.update(ok=False,error=type(e).__name__+': '+str(e).splitlines()[0],waitedSec=round(time.time()-t0,2))
 wt=threading.Thread(target=writer);wt.start();st,h,b=get('CASE-A');wt.join();R.get_doc=orig
 out['concurrent']=dict(getStatus=st,version=b['policy']['version'],events=[e['command'] for e in b['policyAudit']['events']],writer=wres)
 st,h,b=get('CASE-A');out['afterWriter']=dict(status=st,version=b['policy']['version'],events=[e['command'] for e in b['policyAudit']['events']])
 srv.should_exit=True;th.join(10);sock.close();app.state.db.engine.dispose()
print(json.dumps(out,ensure_ascii=False,indent=1))
