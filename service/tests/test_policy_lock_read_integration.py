"""Real SQLite/API measurements. Artificial per-chunk delays explicitly labeled."""
import base64, json, os, platform, sqlite3, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from sqlalchemy import event
import pytest
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.evidence.models import CustodyEventRow
from mcis_service.audit.models import AuditEventRow
from .conftest import make_settings

RESULT = Path(os.environ['MCIS_POLICY_LOCK_RESULTS']) if os.environ.get('MCIS_POLICY_LOCK_RESULTS') else None
CASE='LOCK-SYNTHETIC'; URL=f'/api/v1/cases/{CASE}'
H={'X-MCIS-Role':'LeadInvestigator'}

def record(row):
    if RESULT is None: return
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    with RESULT.open('a') as f: f.write(json.dumps(row, sort_keys=True)+'\n')

@pytest.fixture
def env(tmp_path):
    app=create_app(make_settings(tmp_path,False))
    with app.state.db.session() as s:
        put_doc(s,CaseRow,CASE,CASE,{'caseId':CASE,'schemaVersion':'1.0.0','title':'synthetic','caseEpochUtc':'2026-01-01T00:00:00Z','incidentTimeUtc':'2026-01-01T00:00:00Z','incidentLocation':{'lonDeg':121,'latDeg':31},'isFictionalDemo':True})
        put_doc(s,AccessPolicyRow,CASE,'policy',default_policy())
    starts={};app.state.lock_intervals=[]
    @event.listens_for(app.state.db.engine,'after_cursor_execute')
    def began(conn,cursor,statement,parameters,context,executemany):
        if statement.strip().upper()=='BEGIN IMMEDIATE':starts[id(conn)]=time.perf_counter()
    @event.listens_for(app.state.db.engine,'commit')
    @event.listens_for(app.state.db.engine,'rollback')
    def ended(conn):
        start=starts.pop(id(conn),None)
        if start is not None:app.state.lock_intervals.append(dict(thread=threading.get_ident(),hold_to_commit_or_rollback_callback_s=time.perf_counter()-start))
    with TestClient(app,raise_server_exceptions=False) as c: yield c,app

def register(c,app,mib):
    data=b'x'*(mib*1024*1024)
    r=c.post(URL+'/evidence',headers=H,json={'title':'synthetic','source':'synthetic','extractedBy':'test','extractedUtc':'2026-01-01T00:00:00Z','relativePath':'evidence/EV-001/source.bin','contentBase64':base64.b64encode(data).decode()})
    assert r.status_code==201,r.text
    return app.state.settings.blob_dir/CASE/'evidence/EV-001/source.bin'

def fetch(c,route): return c.get(URL+('/export' if route=='export' else '/evidence/EV-001/content'),headers=H)

@pytest.mark.parametrize('mib',[1,16,64])
@pytest.mark.parametrize('trial',range(3))
def test_natural(env,mib,trial):
    c,app=env;register(c,app,mib)
    t=time.perf_counter();r=fetch(c,'content'); elapsed=time.perf_counter()-t
    assert r.status_code==200 and len(r.content)==mib*1024*1024
    with app.state.db.engine.connect() as conn:
        timeout=conn.exec_driver_sql('PRAGMA busy_timeout').scalar()
        journal=conn.exec_driver_sql('PRAGMA journal_mode').scalar()
    record(dict(kind='natural',mib=mib,trial=trial,elapsed_s=elapsed,status=r.status_code,busy_timeout_ms=timeout,journal=journal,python=sys.version.split()[0],sqlite=sqlite3.sqlite_version,platform=platform.platform(),transaction_intervals=app.state.lock_intervals))

@pytest.mark.parametrize('route',['content','export'])
@pytest.mark.parametrize('mode,delay,timeout',[('sql_revoke_timeout',.8,.15),('sql_revoke_wait',.05,8),('sql_write_wait',.05,8),('api_revoke_timeout',.8,5),('api_revoke_wait',.05,5),('second_get_wait',.8,5),('sql_revoke_after_mismatch',.05,8)])
def test_contenders(env,monkeypatch,route,mode,delay,timeout):
    c,app=env;path=register(c,app,8);inode=path.stat().st_ino
    if mode=='sql_revoke_after_mismatch':path.write_bytes(b'y'*(8*1024*1024))
    original=os.read;entered=threading.Event();reader_thread=[None];chunks=[0];gate_start=[0]
    def slow(fd,count):
        data=original(fd,count)
        if os.fstat(fd).st_ino==inode and threading.get_ident()==reader_thread[0] and data:
            chunks[0]+=1
            if not entered.is_set():gate_start[0]=time.perf_counter();entered.set()
            time.sleep(delay)
        return data
    monkeypatch.setattr(os,'read',slow)
    # Identify actual FastAPI worker thread, not the submitting executor thread.
    from mcis_service.evidence import recorded_content
    real_read=recorded_content.read_content
    def identified(p):
        if reader_thread[0] is None:reader_thread[0]=threading.get_ident()
        return real_read(p)
    monkeypatch.setattr(recorded_content,'read_content',identified)
    policy=default_policy();policy['matrix']['LeadInvestigator']['evidence_meta']='Deny'
    def writer():
        start=time.perf_counter();status=None;error=None
        if mode.startswith('api'):
            r=c.put(URL+'/access-policy',headers=H,json=policy);status=r.status_code;error=r.text if r.status_code>=400 else None
        elif mode=='second_get_wait':status=fetch(c,'content').status_code
        else:
            db=sqlite3.connect(app.state.settings.data_dir/'test.db',timeout=timeout)
            try:
                if mode=='sql_write_wait':db.execute('UPDATE cases SET updated_utc=? WHERE case_id=?',('synthetic marker',CASE))
                else:db.execute('UPDATE access_policies SET doc=? WHERE case_id=?',(json.dumps(policy),CASE))
                db.commit();status='committed'
            except sqlite3.OperationalError as e:db.rollback();status='locked';error=str(e)
            finally:db.close()
        return dict(status=status,error=error,elapsed_s=time.perf_counter()-start)
    start=time.perf_counter()
    with ThreadPoolExecutor(max_workers=2) as pool:
        read=pool.submit(fetch,c,route);assert entered.wait(5)
        w=pool.submit(writer);wr=w.result(timeout=15);response=read.result(timeout=15)
    total=time.perf_counter()-start
    assert response.status_code==(409 if mode=='sql_revoke_after_mismatch' else 200),response.text
    monkeypatch.setattr(os,'read',original)
    monkeypatch.setattr(recorded_content,'read_content',real_read)
    persisted=c.get(URL+'/access-policy',headers=H).json()['matrix']['LeadInvestigator']['evidence_meta']
    follow=fetch(c,'content').status_code
    with app.state.db.session() as s:policy_audits=s.query(AuditEventRow).filter_by(action='policy.update').count()
    record(dict(kind='contention',route=route,mode=mode,mib=8,artificial_delay_per_chunk_s=delay,chunks=chunks[0],writer_timeout_s=timeout,writer=wr,read_status=response.status_code,total_s=total,persisted_permission=persisted,next_get_status=follow,transaction_intervals=app.state.lock_intervals,policy_update_audit_count=policy_audits))
    if mode=='sql_revoke_timeout':assert wr['status']=='locked' and persisted!='Deny' and follow==200
    elif mode=='api_revoke_timeout':assert wr['status']==503 and persisted!='Deny' and follow==200
    elif 'revoke_wait' in mode or mode=='sql_revoke_after_mismatch':assert wr['status'] in (200,'committed') and persisted=='Deny' and follow==403
    else:assert wr['status'] in (200,'committed')
