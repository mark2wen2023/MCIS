import json
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from .test_issue_journal import ready,add
from .conftest import CASE
from mcis_service.investigation import archive as a,journal as j
from mcis_service.identity import local

@pytest.fixture
def bundle(ready):
    t,r,sub,token,i=ready;a.initialize(t.app.state.db)
    add(ready,0,sourceIds=[r['evidenceId']])
    add(ready,1,'verification','反证',outcome='refutes',againstJudgment=1)
    raw=a.export_bundle(t.app.state.db,t.app.state.settings,token,CASE)
    return ready,raw

def test_roundtrip_inert(bundle):
    v,raw=bundle;t,r,sub,token,i=v;db=t.app.state.db
    one=a.restore_bundle(db,token,CASE,raw);two=a.restore_bundle(db,token,CASE,raw)
    assert one['activated'] is False and two['replayed']
    doc=a.read_imported(db,token,CASE,one['sha256'])
    assert doc['payload']['cards'][0]['events'][1]['note']=='反证'
    assert doc['payload']['sources'] and token not in raw.decode()
    with db.session() as s:assert len(list(s.scalars(select(j.Event))))==2

@pytest.mark.parametrize('damage',['hash','source','extra','foreign','seq','authority'])
def test_corrupt_bundle_rejected(bundle,damage):
    v,raw=bundle;t,_,_,token,_=v;wrapper=json.loads(raw);p=wrapper['payload']
    if damage=='hash':wrapper['sha256']='a'*64
    else:
        if damage=='source':p['sources'][next(iter(p['sources']))]='YQ=='
        if damage=='extra':p['token']='forged'
        if damage=='foreign':p['caseId']='FOREIGN'
        if damage=='seq':p['cards'][0]['events'][0]['seq']=2
        if damage=='authority':p['authority']='approved'
        import hashlib
        wrapper['sha256']=hashlib.sha256(a.canonical(p)).hexdigest()
    with pytest.raises(HTTPException):a.restore_bundle(t.app.state.db,token,CASE,a.canonical(wrapper))
    with t.app.state.db.session() as s:assert list(s.scalars(select(a.ImportedArchive)))==[]

def test_changed_source_no_incomplete_export(bundle):
    v,raw=bundle;t,r,_,token,_=v
    (t.app.state.settings.blob_dir/CASE/r['evidence']['relativePath']).write_bytes(b'changed')
    with pytest.raises(HTTPException):a.export_bundle(t.app.state.db,t.app.state.settings,token,CASE)
    assert a.restore_bundle(t.app.state.db,token,CASE,raw)['activated'] is False

def test_restore_needs_current_grant(bundle):
    v,raw=bundle;t,_,sub,token,_=v
    with t.app.state.db.session() as s:j.grant(s,sub,CASE,enabled=False)
    with pytest.raises(HTTPException) as e:a.restore_bundle(t.app.state.db,token,CASE,raw)
    assert e.value.status_code==403
