"""Synthetic concurrency against real local API/SQLite; no authentication claim."""
import base64,hashlib,json,sqlite3,threading
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import event
from .test_evidence_intake_w42 import local,CASE,counts
from .conftest import H
from mcis_service.evidence import service
from mcis_service.redaction.policy import default_policy
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.db import put_doc
URL=f'/api/v1/cases/{CASE}'


def payload(i):
    return {'title':f'Synthetic {i}','source':f'Synthetic source {i}','extractedBy':'Synthetic harness',
            'extractedUtc':'2026-01-01T00:00:00Z','relativePath':f'evidence/synthetic-{i}.bin',
            'contentBase64':base64.b64encode(f'synthetic bytes {i}'.encode()).decode()}


def test_concurrent_registration_never_reuses_or_overwrites_identity(local,monkeypatch):
    c,app=local;barrier=threading.Barrier(4);original=service.next_id
    def overlap(*args):
        eid=original(*args)
        try:barrier.wait(timeout=.3)
        except threading.BrokenBarrierError:pass
        return eid
    monkeypatch.setattr(service,'next_id',overlap)
    with ThreadPoolExecutor(4) as pool:
        responses=list(pool.map(lambda i:c.post(URL+'/evidence',headers=H(),json=payload(i)),range(4)))
    assert [r.status_code for r in responses]==[201]*4
    ids=[r.json()['evidenceId'] for r in responses]
    assert len(set(ids))==4 and counts(app)==(4,4,4)
    for i,eid in enumerate(ids):
        item=c.get(URL+'/evidence/'+eid,headers=H()).json()
        assert item['source']==payload(i)['source'] and item['relativePath']==payload(i)['relativePath']
        raw=f'synthetic bytes {i}'.encode()
        assert item['sha256']==hashlib.sha256(raw).hexdigest()
        assert c.get(URL+'/evidence/'+eid+'/content',headers=H()).content==raw
    assert c.get(URL+'/custody:verify-chain',headers=H()).json()['valid']
    assert c.get(URL+'/audit:verify',headers=H()).json()['valid']


def test_prior_sqlite_writer_revoke_denies_before_file_write(local):
    c,app=local
    with app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',default_policy())
    p=default_policy();p['matrix']['Investigator']['evidence_meta']='Deny'
    db=sqlite3.connect(app.state.settings.data_dir/'test.db');db.execute('BEGIN IMMEDIATE')
    entered=threading.Event()
    @event.listens_for(app.state.db.engine,'before_cursor_execute')
    def observe(*args):
        if args[2]=='BEGIN IMMEDIATE':entered.set()
    try:
        with ThreadPoolExecutor() as pool:
            pending=pool.submit(c.post,URL+'/evidence',headers=H(),json=payload(0))
            assert entered.wait(3)
            db.execute('UPDATE access_policies SET doc=? WHERE case_id=?',(json.dumps(p),CASE));db.commit()
            r=pending.result(timeout=5)
    finally:db.close()
    assert r.status_code==403 and counts(app)==(0,0,0)
    assert not list(app.state.settings.blob_dir.rglob('*.bin'))


def test_reserved_registration_blocks_revocation_until_commit(local,monkeypatch):
    c,app=local;entered=threading.Event();release=threading.Event();original=service.write_blob
    @event.listens_for(app.state.db.engine,'checkout')
    def timeout(conn,*_):conn.execute('PRAGMA busy_timeout=100')
    def held(*a,**kw):
        entered.set();assert release.wait(3);return original(*a,**kw)
    monkeypatch.setattr(service,'write_blob',held)
    p=default_policy();p['matrix']['Investigator']['evidence_meta']='Deny'
    with ThreadPoolExecutor() as pool:
        pending=pool.submit(c.post,URL+'/evidence',headers=H(),json=payload(0))
        assert entered.wait(3)
        try:
            revoke=c.put(URL+'/access-policy',headers=H('LeadInvestigator'),json=p)
            assert revoke.status_code==503 and revoke.json()['detail']['commitState']=='not_committed'
        finally:release.set()
        assert pending.result(timeout=5).status_code==201
    monkeypatch.setattr(service,'write_blob',original)
    assert c.put(URL+'/access-policy',headers=H('LeadInvestigator'),json=p).status_code==200
    before=counts(app);assert c.post(URL+'/evidence',headers=H(),json=payload(1)).status_code==403
    assert counts(app)==before and not (app.state.settings.blob_dir/CASE/'evidence/synthetic-1.bin').exists()
