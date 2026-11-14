import base64,hashlib,json,os,socket,sqlite3,subprocess,sys,threading,time,urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from mcis_service.config import Settings
from mcis_service.main import create_app
from mcis_service.cases.models import CaseRow
from mcis_service.db import put_doc
from mcis_service.evidence.models import EvidenceRow,CustodyEventRow
from mcis_service.audit.models import AuditEventRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
CASE='INDEPENDENT-SYNTHETIC';URL=f'/api/v1/cases/{CASE}'

@pytest.fixture
def local(tmp_path):
    st=Settings();st.data_dir=tmp_path;st.db_url=f'sqlite:///{tmp_path / "test.db"}';st.seed_demo=False
    app=create_app(st)
    case={'caseId':CASE,'schemaVersion':'1.0.0','title':'synthetic','isFictionalDemo':True,'caseEpochUtc':'2026-01-01T00:00:00Z','incidentTimeUtc':'2026-01-01T00:00:00Z','incidentLocation':{'lonDeg':121,'latDeg':31},'displayTimeZoneOffsetMinutes':0}
    with app.state.db.session() as s:put_doc(s,CaseRow,CASE,CASE,case)
    with TestClient(app) as client:yield client,app

def body(i,raw=None):
    raw=raw if raw is not None else f'independent binary {i}'.encode()+b'\xff\x00'
    return {'title':f'Synthetic {i}','source':f'Source {i}','extractedBy':'synthetic','extractedUtc':'2026-01-01T00:00:00Z','fileName':f'sample-{i}.bin','contentBase64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest().upper()}

def counts(app):
    with app.state.db.session() as s:return tuple(s.query(m).count() for m in [EvidenceRow,CustodyEventRow,AuditEventRow])

def tcp(port,path,data=None):
    headers={'X-MCIS-Role':'Investigator'}
    if data is not None:headers['Content-Type']='application/json'
    request=urllib.request.Request(f'http://127.0.0.1:{port}{path}',data=None if data is None else json.dumps(data).encode(),headers=headers)
    with urllib.request.urlopen(request,timeout=15) as r:return r.status,json.load(r)

def test_two_real_tcp_servers_one_sqlite_eight_independent_registrations(local):
    client,app=local;processes=[];logs=[];ports=[]
    try:
        for i in range(2):
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            ports.append(port)
            log=open(app.state.settings.data_dir/f'server-{i}.log','w');logs.append(log)
            process=subprocess.Popen([sys.executable,str(Path(__file__).with_name('server.py')),str(app.state.settings.data_dir),str(port)],stdout=log,stderr=log,env=os.environ.copy());processes.append(process)
            deadline=time.monotonic()+15
            while True:
                assert process.poll() is None,'server exited during startup'
                try:tcp(port,'/openapi.json');break
                except OSError:
                    assert time.monotonic()<deadline
                    time.sleep(.05)
        gate=threading.Barrier(8)
        def post(i):gate.wait(timeout=5);return tcp(ports[i%2],URL+'/evidence',body(i))
        with ThreadPoolExecutor(8) as pool:results=list(pool.map(post,range(8)))
        assert [r[0] for r in results]==[201]*8
        ids=[r[1]['evidenceId'] for r in results];assert len(set(ids))==8
        assert counts(app)==(8,8,8)
        for i,(_,item) in enumerate(results):
            raw=base64.b64decode(body(i)['contentBase64'])
            assert item['sha256']==hashlib.sha256(raw).hexdigest()
            assert (app.state.settings.blob_dir/CASE/item['relativePath']).read_bytes()==raw
            got=client.get(URL+'/evidence/'+item['evidenceId']).json()
            assert got['source']==body(i)['source'] and got['relativePath']==item['relativePath']
        assert len(list(app.state.settings.blob_dir.rglob('*.bin')))==8
        assert client.get(URL+'/custody:verify-chain').json()['valid']
        assert client.get(URL+'/audit:verify').json()['valid']
    finally:
        for process in processes:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        for log in logs:log.close()

@pytest.mark.parametrize('change',[{'contentBase64':'Zh=='},{'contentBase64':'!!'},{'sha256':'0'*64},{'sha256':'z'*64}])
def test_strict_rejection_does_not_write_and_releases_reservation(local,change):
    client,app=local
    response=client.post(URL+'/evidence',json={**body(0),**change})
    assert response.status_code==422
    assert counts(app)==(0,0,0) and not list(app.state.settings.blob_dir.rglob('*.bin'))
    connection=sqlite3.connect(app.state.settings.data_dir/'test.db',timeout=.1)
    try:connection.execute('BEGIN IMMEDIATE');connection.rollback()
    finally:connection.close()
    good=client.post(URL+'/evidence',json=body(1,b''))
    assert good.status_code==201 and counts(app)==(1,1,1)
    assert (app.state.settings.blob_dir/CASE/good.json()['relativePath']).read_bytes()==b''

def test_prior_external_sqlite_revoke_seen_before_registration(local):
    client,app=local;p=default_policy()
    with app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',p)
    connection=sqlite3.connect(app.state.settings.data_dir/'test.db');connection.execute('BEGIN IMMEDIATE')
    entered=threading.Event()
    def observe(conn,cursor,statement,*args):
        if statement=='BEGIN IMMEDIATE':entered.set()
    event.listen(app.state.db.engine,'before_cursor_execute',observe)
    try:
        with ThreadPoolExecutor(1) as pool:
            pending=pool.submit(client.post,URL+'/evidence',json=body(0))
            assert entered.wait(3)
            p['matrix']['Investigator']['evidence_meta']='Deny'
            connection.execute('UPDATE access_policies SET doc=? WHERE case_id=?',(json.dumps(p),CASE));connection.commit()
            assert pending.result(timeout=5).status_code==403
    finally:connection.close();event.remove(app.state.db.engine,'before_cursor_execute',observe)
    assert counts(app)==(0,0,0) and not list(app.state.settings.blob_dir.rglob('*.bin'))

def test_same_explicit_path_one_success_no_content_overwrite(local):
    client,app=local;gate=threading.Barrier(2)
    def post(i):
        gate.wait(timeout=3)
        return client.post(URL+'/evidence',json={**body(i),'relativePath':'evidence/shared.bin'})
    with ThreadPoolExecutor(2) as pool:responses=list(pool.map(post,range(2)))
    assert sorted(r.status_code for r in responses)==[201,409]
    winner=next(i for i,r in enumerate(responses) if r.status_code==201)
    assert counts(app)==(1,1,1)
    assert (app.state.settings.blob_dir/CASE/'evidence/shared.bin').read_bytes()==base64.b64decode(body(winner)['contentBase64'])
    with app.state.db.session() as s:
        assert s.query(EvidenceRow).one().doc['source']==body(winner)['source']

def test_denied_role_before_strict_base64_validation(local):
    client,app=local
    response=client.post(URL+'/evidence',headers={'X-MCIS-Role':'Public'},json={**body(0),'contentBase64':'!!'})
    assert response.status_code==403 and counts(app)==(0,0,0)
    assert not list(app.state.settings.blob_dir.rglob('*.bin'))
