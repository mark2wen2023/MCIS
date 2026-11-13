import uuid
import pytest
from .test_issue_journal import ready
from .test_identity_http_trial import trial,headers
from .conftest import CASE
from mcis_service.investigation import journal
from mcis_service.identity import local
URL=f'/api/v1/trial/cases/{CASE}/issues'
def body(v):return {'issueId':v[4],'operationId':str(uuid.uuid4()),'entry':{'kind':'judgment','note':'初判'}}

def test_http_lifecycle(ready):
    t,_,_,token,i=ready;b=body(ready)
    with trial(t) as api:
        first=api.post(URL,headers=headers(token),json=b);assert first.status_code==201,first.text
        assert api.post(URL,headers=headers(token),json=b).json()['replayed']
        for seq,kind,outcome in [(1,'verification','inconclusive'),(2,'discussion',None)]:
            entry={'kind':kind,'note':'核实或讨论的记录','againstJudgment':1}
            if outcome:entry['outcome']=outcome
            r=api.post(URL+'/'+i+'/events',headers=headers(token),json={'operationId':str(uuid.uuid4()),'expectedRevision':seq,'entry':entry})
            assert r.status_code==200,r.text
        r=api.get(URL+'/'+i,headers=headers(token));assert r.json()['revision']==3
        assert r.json()['events'][0]['note']=='初判' and r.json()['status']=='working_unreviewed'
        assert api.get(URL,headers=headers(token)).json()['items'][0]['revision']==3
        assert r.headers['cache-control']=='no-store' and token not in r.text

@pytest.mark.parametrize('extra',[{'X-MCIS-Role':'LeadInvestigator'},{'X-MCIS-Operator':'fake'},{'Origin':'http://evil'},{'Cookie':'secret=x'}])
def test_denied_transport(ready,extra):
    with trial(ready[0]) as api:
        r=api.post(URL,headers={**headers(ready[3]),**extra},json=body(ready))
    assert r.status_code==400 and journal.list_issues(ready[0].app.state.db,ready[3],CASE)['items']==[]

@pytest.mark.parametrize('raw',['{}','{"issueId":"a","issueId":"b"}','{"n":NaN}','['*1100+']'*1100,'x'*65537])
def test_invalid_json(ready,raw):
    with trial(ready[0]) as api:r=api.post(URL,headers=headers(ready[3]),content=raw)
    assert r.status_code in (413,422) and '初判' not in r.text

def test_write_grant_rechecked_read_still_allowed(ready):
    t,_,sub,token,i=ready
    with trial(t) as api:
        assert api.post(URL,headers=headers(token),json=body(ready)).status_code==201
        with t.app.state.db.session() as s:journal.grant(s,sub,CASE,enabled=False)
        assert api.post(URL,headers=headers(token),json=body(ready)).status_code==403
        assert api.get(URL+'/'+i,headers=headers(token)).status_code==200
        with t.app.state.db.session() as s:local.revoke_session(s,token)
        assert api.get(URL+'/'+i,headers=headers(token)).status_code==403

@pytest.mark.parametrize('suffix,method',[('/','get'),('?role=LeadInvestigator','get'),('/bad','get'),('','delete'),('/00000000-0000-0000-0000-000000000000/events','get')])
def test_exact_routes(ready,suffix,method):
    with trial(ready[0]) as api:r=getattr(api,method)(URL+suffix,headers=headers(ready[3]))
    assert r.status_code==404
