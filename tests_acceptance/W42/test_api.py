"""Black-box contract assertions plus explicit fault/tamper injection on isolated data."""
import base64
import copy
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from sqlalchemy import select,text
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from mcis_service.evidence.models import EvidenceRow,CustodyEventRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.db import put_doc
from conftest import *

@pytest.mark.parametrize('raw',[b'',bytes(range(256))*4,b'\xff\x00<script>window.pwned=1</script>'])
def test_lifecycle_preview_zero_write(env,raw):
    app,c,root=env;b=payload(raw);before=snapshot(env)
    p=preview(c,b);assert snapshot(env)==before
    assert p['sourceSha256']==hashlib.sha256(raw).hexdigest() and p['byteLength']==len(raw)
    r=commit(c,b);assert r['metadata']=={k:b[k] for k in ('title','source','extractedBy','extractedUtc','category','confidentiality','note')}
    assert r['registeredUtc']!=b['extractedUtc'] and r['registeredBy']=='Independent-Operator'
    assert r['evidence']['status']=='Unverified'
    saved=snapshot(env)
    for url in (C+'/evidence-intakes/'+r['requestDigest'],C+'/evidence/'+r['evidenceId']+'/intake'):
        rr=c.get(url,headers=H);assert rr.status_code==200,rr.text
        assert rr.json()['metadata']==r['metadata'];assert snapshot(env)==saved
    rr=commit(c,b);assert rr['replayed'] is True and rr['evidenceId']==r['evidenceId'];assert snapshot(env)==saved
    url=C+'/evidence-intakes/'+r['requestDigest']+':download'
    for invalid in ({},{'purpose':''},{'purpose':'  '},{'purpose':'x','extra':1},{'purpose':'x'*1001}):
        assert c.post(url,json=invalid,headers=H).status_code==422
    assert snapshot(env)==saved
    dl=c.post(url,json={'purpose':'Independent byte equality check'},headers=H)
    assert dl.status_code==200 and dl.content==raw and dl.headers['x-sha256']==hashlib.sha256(raw).hexdigest()
    after=snapshot(env);assert len(after[0]['custody_events'])==len(saved[0]['custody_events'])+1
    assert len(after[0]['audit_events'])==len(saved[0]['audit_events'])+1

@pytest.mark.parametrize('field,value',[('fileName','../x'),('fileName','a\\b'),('fileName','.'),('fileName','a\x00'),('fileName','x'*129),('title',' '),('title','x'*1001),('source',''),('extractedBy','x'*201),('note','x'*2001),('category','Auto'),('confidentiality','Public'),('extractedUtc','2020-01-01T00:00:00'),('extractedUtc','2020-01-01T00:00:00.0Z'),('extractedUtc','2020-01-01T00:00:00+00:00'),('extractedUtc','0001-01-01T00:00:00Z'),('extractedUtc','0999-01-01T00:00:00Z'),('extractedUtc','2023-02-29T00:00:00Z'),('extractedUtc',None),('contentBase64','YQ'),('contentBase64','YQ==\n'),('contentBase64','YR==')])
def test_invalid_fields_zero_write(env,field,value):
    _,c,_=env;b=payload();b[field]=value;before=snapshot(env)
    assert c.post(C+'/evidence-intakes:preview',json=b,headers=H).status_code==422
    assert snapshot(env)==before

@pytest.mark.parametrize('stamp',['1000-01-01T00:00:00Z','9999-12-31T23:59:59Z','2000-02-29T00:00:00Z'])
def test_supported_dates(env,stamp):
    _,c,_=env;b=payload();b['extractedUtc']=stamp
    r=commit(c,b);assert c.get(C+'/evidence-intakes/'+r['requestDigest'],headers=H).status_code==200

@pytest.mark.parametrize('kind',['duplicate','unknown','nonfinite','nesting','utf8','missing'])
def test_invalid_json(env,kind):
    _,c,_=env;b=payload();s=json.dumps(b)
    if kind=='duplicate':s=s[:-1]+',"title":"duplicate"}'
    if kind=='unknown':s=s[:-1]+',"unknown":1}'
    if kind=='nonfinite':s=s[:-1]+',"unknown":NaN}'
    if kind=='nesting':s='['*2000+'0'+']'*2000
    if kind=='missing':b.pop('extractedUtc');s=json.dumps(b)
    data=s.encode() if kind!='utf8' else b'\xff'
    before=snapshot(env);r=c.post(C+'/evidence-intakes:preview',content=data,headers={**H,'Content-Type':'application/json'})
    assert r.status_code==422,r.text;assert snapshot(env)==before

def test_budgets(env):
    _,c,_=env;b=payload(b'\x7f'*(8*1024*1024));before=snapshot(env)
    assert preview(c,b)['byteLength']==8*1024*1024
    b['contentBase64']=base64.b64encode(b'x'*(8*1024*1024+1)).decode()
    assert c.post(C+'/evidence-intakes:preview',json=b,headers=H).status_code==413
    small=json.dumps(payload()).encode();exact=small+b' '*(12*1024*1024-len(small))
    headers={**H,'Content-Type':'application/json'}
    assert c.post(C+'/evidence-intakes:preview',content=exact,headers=headers).status_code==200
    assert c.post(C+'/evidence-intakes:preview',content=exact+b' ',headers=headers).status_code==413
    assert snapshot(env)==before

def test_binding_confirmation(env):
    _,c,_=env;b=payload();p=preview(c,b);body={**b,'requestDigest':p['requestDigest'],'confirmed':True};before=snapshot(env)
    for change in ({'confirmed':False},{'confirmed':1}):assert c.post(C+'/evidence-intakes:commit',json={**body,**change},headers=H).status_code==422
    for change in ({'title':'changed'},{'contentBase64':'AA=='},{'note':'changed'}):assert c.post(C+'/evidence-intakes:commit',json={**body,**change},headers=H).status_code==409
    for headers in ({**H,'X-MCIS-Operator':'Other'},{**H,'X-MCIS-Role':'LeadInvestigator'}):assert c.post(C+'/evidence-intakes:commit',json=body,headers=headers).status_code==409
    assert snapshot(env)==before

@pytest.mark.parametrize('same',[True,False])
def test_concurrent_requests(env,same):
    _,c,_=env
    bodies=[payload() for _ in range(6)]
    if not same:
        for i,b in enumerate(bodies):b['note']=str(i)
    reqs=[{**b,'requestDigest':preview(c,b)['requestDigest'],'confirmed':True} for b in bodies]
    before=snapshot(env)
    with ThreadPoolExecutor(max_workers=6) as pool: responses=list(pool.map(lambda b:c.post(C+'/evidence-intakes:commit',json=b,headers=H),reqs))
    assert all(r.status_code==200 for r in responses),[(r.status_code,r.text) for r in responses]
    n=1 if same else 6;assert len({r.json()['evidenceId'] for r in responses})==n
    after=snapshot(env)
    for table in before[0]:assert len(after[0][table])-len(before[0][table])==n
    assert len(after[1])-len(before[1])==n

@pytest.mark.parametrize('kind',['existing','leaf_symlink','parent_symlink'])
def test_no_overwrite_path(env,kind):
    app,c,root=env;b=payload();d=preview(c,b)['requestDigest'];path=root/'blobs'/CASE/'raw/evidence-intakes'/d/'source.bin'
    outside=root/'sentinel';outside.write_bytes(b'KEEP')
    if kind=='parent_symlink':
        path.parent.parent.mkdir(parents=True);path.parent.symlink_to(root,target_is_directory=True)
    else:
        path.parent.mkdir(parents=True)
        if kind=='existing':path.write_bytes(b'KEEP')
        else:path.symlink_to(outside)
    before=snapshot(env);r=c.post(C+'/evidence-intakes:commit',json={**b,'requestDigest':d,'confirmed':True},headers=H)
    assert r.status_code==409,r.text;assert snapshot(env)==before;assert outside.read_bytes()==b'KEEP'

@pytest.mark.parametrize('fault',['commit','write','cleanup'])
def test_actual_failure_rollback(env,monkeypatch,fault):
    app,c,root=env;b=payload();d=preview(c,b)['requestDigest'];before=snapshot(env)
    original_commit=Session.commit
    def fail_commit(s):
        # Fail at actual transaction commit after file/evidence/register/audit exist, not at audit helper.
        if s.info.get('w42_written') or s.connection().exec_driver_sql('SELECT COUNT(*) FROM evidence_items').scalar():raise RuntimeError('independent DB commit fault')
        return original_commit(s)
    if fault in ('commit','cleanup'):monkeypatch.setattr(Session,'commit',fail_commit)
    if fault=='write':
        original_fsync=os.fsync
        def fail_fsync(fd):raise OSError('independent file fsync fault')
        monkeypatch.setattr(os,'fsync',fail_fsync)
    if fault=='cleanup':
        original_unlink=Path.unlink
        def fail_unlink(p,*a,**kw):
            if p.name=='source.bin':raise OSError('independent cleanup fault')
            return original_unlink(p,*a,**kw)
        monkeypatch.setattr(Path,'unlink',fail_unlink)
    r=c.post(C+'/evidence-intakes:commit',json={**b,'requestDigest':d,'confirmed':True},headers=H)
    assert r.status_code==500,r.text
    after=snapshot(env);assert after[0]==before[0]
    if fault=='cleanup':assert r.json()['code']=='INTAKE_CLEANUP_FAILED' and len(after[1])==1
    else:assert after[1]==before[1]

@pytest.mark.parametrize('mode',['role','read_only','denied','restricted_rule','testimony'])
def test_policy_all_endpoints(env,mode):
    app,c,_=env;b=payload();r=commit(c,b);headers=H
    if mode=='role':headers={**H,'X-MCIS-Role':'ExternalExpert'}
    else:
        p=default_policy()
        if mode=='read_only':p['matrix']['Investigator']['evidence_meta']='ReadOnly'
        if mode=='denied':p['matrix']['Investigator']['evidence_meta']='Deny'
        if mode=='testimony':p['matrix']['Investigator']['testimony']='Deny'
        if mode=='restricted_rule':p['fieldRules'].append({'field':'evidence.restricted','method':'Remove','appliesTo':['Investigator']})
        with app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',p)
    before=snapshot(env)
    for action in ('preview','commit'):
        body=b if action=='preview' else {**b,'requestDigest':r['requestDigest'],'confirmed':True}
        resp=c.post(C+'/evidence-intakes:'+action,json=body,headers=headers);assert resp.status_code==403,resp.text
    allowed=200 if mode=='read_only' else 403
    for url in (C+'/evidence-intakes/'+r['requestDigest'],C+'/evidence/'+r['evidenceId']+'/intake'):
        rr=c.get(url,headers=headers);assert rr.status_code==allowed,rr.text
    assert snapshot(env)==before
    dl=c.post(C+'/evidence-intakes/'+r['requestDigest']+':download',json={'purpose':'check'},headers=headers)
    assert dl.status_code==allowed,dl.text

@pytest.mark.parametrize('kind',['bytes','missing','metadata','path','register','change'])
def test_tamper_fail_closed(env,kind):
    app,c,root=env;b=payload();r=commit(c,b);d=r['requestDigest'];path=root/'blobs'/CASE/'raw/evidence-intakes'/d/'source.bin'
    if kind=='bytes':path.write_bytes(b'altered')
    elif kind=='missing':path.unlink()
    elif kind in ('metadata','path'):
        with app.state.db.session() as s:
            row=s.scalars(select(EvidenceRow).where(EvidenceRow.key==r['evidenceId'])).one();doc=dict(row.doc)
            doc['title' if kind=='metadata' else 'relativePath']='tampered';row.doc=doc
    elif kind=='register':
        with app.state.db.engine.begin() as conn:
            conn.execute(text('DROP TRIGGER custody_events_no_update'))
            conn.execute(text("UPDATE custody_events SET detail = replace(detail, '原登记', '被篡改') WHERE kind='Register'"))
    else:
        from mcis_service.evidence.service import append_custody
        with app.state.db.session() as s:append_custody(s,case_id=CASE,evidence_id=r['evidenceId'],kind='Change',operator='synthetic',role='Investigator',sha256=r['sourceSha256'],detail='unsupported change')
    before=snapshot(env)
    assert c.get(C+'/evidence-intakes/'+d,headers=H).status_code==409
    assert c.post(C+'/evidence-intakes/'+d+':download',json={'purpose':'check'},headers=H).status_code==409
    assert c.post(C+'/evidence-intakes:commit',json={**b,'requestDigest':d,'confirmed':True},headers=H).status_code==409
    assert snapshot(env)==before

def test_note_edit_and_fresh_mcase(env,tmp_path):
    app,c,root=env;raw=bytes(range(256));b=payload(raw);r=commit(c,b)
    assert c.patch(C+'/evidence/'+r['evidenceId'],json={'note':'Later legitimate note'},headers=H).status_code==200
    url=C+'/evidence-intakes/'+r['requestDigest'];rr=c.get(url,headers=H)
    assert rr.status_code==200,rr.text;assert rr.json()['metadata']['note']==b['note']
    assert rr.json()['evidence']['note']=='Later legitimate note'
    assert c.post(url+':download',json={'purpose':'roundtrip source'},headers=H).status_code==200
    with app.state.db.engine.connect() as conn:lines=conn.execute(text('SELECT line FROM custody_events ORDER BY seq')).scalars().all()
    package=c.get(C+'/export',headers=H);assert package.status_code==200,package.text
    fresh=application(tmp_path/'fresh')
    with TestClient(fresh,raise_server_exceptions=False) as other:
        imported=other.post('/api/v1/cases:import',content=package.content,headers={**H,'Content-Type':'application/zip'})
        assert imported.status_code==201,imported.text
        reread=other.get(url,headers=H);assert reread.status_code==200,reread.text
        assert reread.json()['metadata']==r['metadata'];assert reread.json()['evidence']['note']=='Later legitimate note'
        with fresh.state.db.engine.connect() as conn:assert conn.execute(text('SELECT line FROM custody_events ORDER BY seq')).scalars().all()==lines
        dl=other.post(url+':download',json={'purpose':'fresh DB bytes'},headers=H);assert dl.status_code==200 and dl.content==raw
    fresh.state.db.engine.dispose()

@pytest.mark.parametrize('role',['ExternalExpert','InterestedState','AgentService','Public'])
def test_every_noninvestigator_role(env,role):
    _,c,_=env;b=payload();r=commit(c,b);headers={**H,'X-MCIS-Role':role};before=snapshot(env)
    assert c.post(C+'/evidence-intakes:preview',json=b,headers=headers).status_code==403
    assert c.post(C+'/evidence-intakes:commit',json={**b,'requestDigest':r['requestDigest'],'confirmed':True},headers=headers).status_code==403
    assert c.get(C+'/evidence-intakes/'+r['requestDigest'],headers=headers).status_code==403
    assert c.get(C+'/evidence/'+r['evidenceId']+'/intake',headers=headers).status_code==403
    assert c.post(C+'/evidence-intakes/'+r['requestDigest']+':download',json={'purpose':'test'},headers=headers).status_code==403
    assert snapshot(env)==before

def test_full_eight_mib_and_max_metadata(env):
    _,c,_=env;raw=b'\xff'*(8*1024*1024);b=payload(raw)
    b.update(title='标'*1000,source='来'*1000,extractedBy='人'*200,note='记'*2000,fileName='文'*124+'.bin')
    r=commit(c,b);assert r['byteLength']==len(raw)
    dl=c.post(C+'/evidence-intakes/'+r['requestDigest']+':download',json={'purpose':'max boundary'},headers=H)
    assert dl.status_code==200 and dl.content==raw

def test_legacy_evidence_not_migrated(env):
    _,c,_=env;b=payload(b'legacy');old={k:v for k,v in b.items() if k!='profile'}
    r=c.post(C+'/evidence',json=old,headers=H);assert r.status_code==201,r.text
    eid=r.json()['evidenceId'];before=snapshot(env)
    rr=c.get(C+'/evidence/'+eid+'/intake',headers=H);assert rr.status_code==404 and rr.json()['code']=='INTAKE_NOT_FOUND'
    assert snapshot(env)==before

@pytest.mark.parametrize('kind',['missing_evidence','missing_register','duplicate_register'])
def test_incomplete_records_fail_closed(env,kind):
    app,c,_=env;b=payload();r=commit(c,b);d=r['requestDigest']
    with app.state.db.engine.begin() as conn:
        if kind=='missing_evidence':conn.execute(text('DELETE FROM evidence_items'))
        elif kind=='missing_register':
            conn.execute(text('DROP TRIGGER custody_events_no_delete'));conn.execute(text('DELETE FROM custody_events'))
        else:
            conn.execute(text('INSERT INTO custody_events (case_id,seq,evidence_id,kind,utc,operator,sha256,previous_sha256,detail,verify_matched,prev_line_hash,line) SELECT case_id,seq+1,evidence_id,kind,utc,operator,sha256,previous_sha256,detail,verify_matched,prev_line_hash,line FROM custody_events'))
    before=snapshot(env)
    assert c.get(C+'/evidence-intakes/'+d,headers=H).status_code==409
    assert c.post(C+'/evidence-intakes:commit',json={**b,'requestDigest':d,'confirmed':True},headers=H).status_code==409
    assert snapshot(env)==before

@pytest.mark.parametrize('category',['evidence_meta','testimony'])
def test_redacted_is_not_full_read(env,category):
    app,c,_=env;b=payload();r=commit(c,b);p=default_policy();p['matrix']['Investigator'][category]='Redacted'
    with app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',p)
    before=snapshot(env)
    assert c.post(C+'/evidence-intakes:preview',json=b,headers=H).status_code==403
    assert c.post(C+'/evidence-intakes:commit',json={**b,'requestDigest':r['requestDigest'],'confirmed':True},headers=H).status_code==403
    assert c.get(C+'/evidence-intakes/'+r['requestDigest'],headers=H).status_code==403
    assert c.get(C+'/evidence/'+r['evidenceId']+'/intake',headers=H).status_code==403
    assert c.post(C+'/evidence-intakes/'+r['requestDigest']+':download',json={'purpose':'no full read'},headers=H).status_code==403
    assert snapshot(env)==before

@pytest.mark.parametrize('operator',['x'*201,'%20%20','bad%00operator','bad%0Aoperator'])
def test_download_operator_bounded(env,operator):
    _,c,_=env;r=commit(c,payload());before=snapshot(env)
    resp=c.post(C+'/evidence-intakes/'+r['requestDigest']+':download',json={'purpose':'operator check'},headers={**H,'X-MCIS-Operator':operator})
    assert resp.status_code==422,resp.text;assert snapshot(env)==before
