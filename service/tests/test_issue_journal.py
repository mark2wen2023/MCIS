import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import select,update,delete
from .test_internal_unreviewed_save import setup
from .test_local_authority import provision
from .conftest import CASE
from mcis_service.identity import local
from mcis_service.investigation import journal as j

@pytest.fixture
def ready(client,empty_client,monkeypatch):
    t,r,_=setup(client,empty_client,monkeypatch);subject,token=provision(t)
    j.initialize(t.app.state.db)
    with t.app.state.db.session() as s:j.grant(s,subject,CASE,enabled=True)
    return t,r,subject,token,str(uuid.uuid4())

def add(v,seq,kind='judgment',note='初步判断',**kw):
    t,r,sub,token,i=v
    return j.append(t.app.state.db,t.app.state.settings,token,CASE,i,kw.pop('op',str(uuid.uuid4())),seq,{'kind':kind,'note':note,**kw})

def test_progressive_preservation(ready):
    v=ready;t,r,sub,token,i=v
    a=add(v,0,sourceIds=[r['evidenceId']]);assert a['revision']==1
    add(v,1,'verification','核实得到反证',outcome='refutes',againstJudgment=1)
    add(v,2,'judgment','依据新材料改变判断')
    with pytest.raises(HTTPException) as e:add(v,3,'discussion','尚不能讨论',againstJudgment=3)
    assert e.value.status_code==409
    add(v,3,'verification','尚不能确定',outcome='inconclusive',againstJudgment=3)
    last=add(v,4,'discussion','保留分歧，继续补证',againstJudgment=3)
    read=j.read(t.app.state.db,token,CASE,i)
    assert read['revision']==5 and read['events'][0]['note']=='初步判断'
    assert read['events'][2]['note']=='依据新材料改变判断' and read['status']=='working_unreviewed'
    assert read['events'][0]['sourceSnapshots'][0]['evidenceId']==r['evidenceId']
    assert len(j.list_issues(t.app.state.db,token,CASE)['items'])==1
    assert token not in str(read)

def test_idempotency_conflict(ready):
    op=str(uuid.uuid4());one=add(ready,0,op=op);again=add(ready,0,op=op)
    assert again['replayed'] and again['revision']==1
    with pytest.raises(HTTPException) as e:add(ready,0,op=op,note='换内容')
    assert e.value.status_code==409
    with pytest.raises(HTTPException):add(ready,0)

@pytest.mark.parametrize('change',['grant','session','member'])
def test_revocation(ready,change):
    t,_,sub,token,i=ready;op=str(uuid.uuid4());add(ready,0,op=op)
    with t.app.state.db.session() as s:
        if change=='grant':j.grant(s,sub,CASE,enabled=False)
        elif change=='session':local.revoke_session(s,token)
        else:local.set_membership(s,sub,CASE,role='LeadInvestigator',enabled=False)
    with pytest.raises(HTTPException) as e:add(ready,0,op=op)
    assert e.value.status_code==403
    if change=='grant':assert j.read(t.app.state.db,token,CASE,i)['revision']==1
    else:
        with pytest.raises(HTTPException):j.read(t.app.state.db,token,CASE,i)

@pytest.mark.parametrize('kind,outcome,ref',[('verification','supports',1),('discussion',None,1)])
def test_no_initial_nonjudgment(ready,kind,outcome,ref):
    with pytest.raises(HTTPException):add(ready,0,kind,outcome=outcome,againstJudgment=ref)

def test_stale_reference(ready):
    add(ready,0);add(ready,1)
    with pytest.raises(HTTPException):add(ready,2,'verification',outcome='supports',againstJudgment=1)

def test_corrupt_source(ready):
    t,r,_,_,_=ready
    (t.app.state.settings.blob_dir/CASE/r['evidence']['relativePath']).write_bytes(b'changed')
    with pytest.raises(HTTPException):add(ready,0,sourceIds=[r['evidenceId']])
    with t.app.state.db.session() as s:assert list(s.scalars(select(j.Event)))==[]

def test_history_db_append_only(ready):
    add(ready,0);t,*_=ready
    for statement in (update(j.Event).values(doc={}),delete(j.Event)):
        with pytest.raises(Exception):
            with t.app.state.db.session() as s:s.execute(statement)

def test_foreign_case(ready):
    t,r,sub,token,i=ready;add(ready,0)
    with pytest.raises(HTTPException) as e:j.read(t.app.state.db,token,'FOREIGN',i)
    assert e.value.status_code==403
