"""Synthetic probe: timing/thread evidence for the 'database is locked' root cause (outside repo)."""
import sys,tempfile,threading,time,sqlite3
from pathlib import Path
sys.path.insert(0,'.');sys.path.insert(0,'../tests_acceptance/W171')
import test_workbench as T
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.access_workbench import router as R
print('sqlite3 default busy timeout (python connect timeout) = 5.0s; sqlite lib',sqlite3.sqlite_version)
def setup(tmp):
    app=create_app(Settings(data_dir=Path(tmp),seed_demo=False))
    with app.state.db.session() as s:put_doc(s,CaseRow,'CASE-A','CASE-A',{'caseId':'CASE-A','title':'CASE-A'})
    return app
def write_v2(app):
    with app.state.db.session() as o:
        p=default_policy();p['version']='2.0.0';put_doc(o,AccessPolicyRow,'CASE-A','policy',p);T.event(o,command='version-2')
# A: ORIGINAL test scheduling: nested write inside get_doc, on the request thread
with tempfile.TemporaryDirectory() as tmp:
    app=setup(tmp)
    with TestClient(app) as c:
        T.save(c);orig=R.get_doc;st={}
        def raced(session,model,cid,key):
            r=orig(session,model,cid,key);t0=time.time()
            st['thread']=threading.current_thread().name;st['in_tx']=session.connection().connection.driver_connection.in_transaction
            try:write_v2(app);st['write']='ok'
            except Exception as e:st['write']=type(e).__name__+': '+str(e).splitlines()[0]
            st['waited']=round(time.time()-t0,2);return r
        R.get_doc=raced;t=time.time();resp=c.get(T.url());R.get_doc=orig
        print('A original-schedule: handler thread=%s holds_write_tx=%s | nested writer on SAME thread -> %s after %.2fs | GET -> %s (total %.2fs)'%(st['thread'],st['in_tx'],st['write'],st['waited'],resp.status_code,time.time()-t))
# B: real concurrency: writer in a SEPARATE thread, reader paused mid-transaction
with tempfile.TemporaryDirectory() as tmp:
    app=setup(tmp)
    with TestClient(app) as c:
        T.save(c);orig=R.get_doc;ev={'reading':threading.Event(),'release':threading.Event()};wr={}
        def slow(session,model,cid,key):
            r=orig(session,model,cid,key)
            if not ev['reading'].is_set():
                ev['reading'].set();ev['release'].wait(10)
            return r
        def writer():
            ev['reading'].wait(10);t0=time.time()
            try:write_v2(app);wr['ok']=True
            except Exception as e:wr['ok']=False;wr['err']=type(e).__name__+': '+str(e).splitlines()[0]
            wr['waited']=round(time.time()-t0,2)
        R.get_doc=slow;th=threading.Thread(target=writer);th.start()
        rt=[None];g=threading.Thread(target=lambda:rt.__setitem__(0,c.get(T.url())));g.start()
        ev['reading'].wait(10);time.sleep(.5);print('B separate-thread writer still blocked while reader holds tx:',th.is_alive());ev['release'].set();g.join();th.join();R.get_doc=orig
        d=rt[0].json();print('B GET',rt[0].status_code,'version',d['policy']['version'],'events',[e['command'] for e in d['policyAudit']['events']],'| writer',wr)
        d2=c.get(T.url()).json();print('B next GET version',d2['policy']['version'],[e['command'] for e in d2['policyAudit']['events']])
