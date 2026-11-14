import asyncio,uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from .test_issue_journal import ready
from .test_issue_host_bridge import request
from .test_issue_host_sources import message,client
from .test_identity_http_trial import trial,headers
from .conftest import CASE
from mcis_service.investigation import journal as j


def setup_pin(v):
    t,r,_,token,_=v
    with trial(t) as api:source=api.get(f'/api/v1/trial/cases/{CASE}/sources',headers=headers(token)).json()['items'][0]
    return {k:source[k] for k in ('evidenceId','sourceIncarnation','sourceSha256')}
def count(v):
    with v[0].app.state.db.session() as s:return len(list(s.scalars(select(j.Event))))
def append(v,pins,op=None):
    t,r,_,token,i=v
    return j.append(t.app.state.db,t.app.state.settings,token,CASE,i,op or str(uuid.uuid4()),0,{'kind':'judgment','note':'待核实','sourceIds':[r['evidenceId']]},source_pins=pins)

@pytest.mark.parametrize('part',['sourceIncarnation','sourceSha256'])
def test_stale_selection_no_write(ready,part):
    pin=setup_pin(ready);pin[part]=str(uuid.uuid4()) if part=='sourceIncarnation' else '0'*64
    with pytest.raises(HTTPException) as e:append(ready,[pin])
    assert e.value.status_code==409 and e.value.detail['code']=='SOURCE_SELECTION_CHANGED' and count(ready)==0

@pytest.mark.parametrize('damage',['missing','duplicate','extra','unknown'])
def test_pin_shape_set_invalid(ready,damage):
    pin=setup_pin(ready);pins=[pin]
    if damage=='missing':pins=[]
    elif damage=='duplicate':pins*=2
    elif damage=='extra':pins.append({**pin,'evidenceId':'EV-OTHER'})
    else:pin['role']='LeadInvestigator'
    with pytest.raises((HTTPException,ValueError)):append(ready,pins)
    assert count(ready)==0


def test_replay_original_pins_historical_not_rechecked(ready,monkeypatch):
    pin=setup_pin(ready);op=str(uuid.uuid4());assert not append(ready,[pin],op)['replayed']
    monkeypatch.setattr(j,'source_current',lambda *a:pytest.fail('replay must not attest current source'))
    assert append(ready,[pin],op)['replayed'] and count(ready)==1
    with pytest.raises(HTTPException) as e:append(ready,[{**pin,'sourceSha256':'0'*64}],op)
    assert e.value.detail['code']=='ISSUE_OPERATION_CONFLICT'


def test_final_source_change_rollsback(ready,monkeypatch):
    pin=setup_pin(ready);old=j.source_current;calls=0
    def current(*args):
        nonlocal calls
        calls+=1;value=old(*args)
        return {**value,'incarnation':str(uuid.uuid4())} if calls==2 else value
    monkeypatch.setattr(j,'source_current',current)
    with pytest.raises(HTTPException) as e:append(ready,[pin])
    assert e.value.detail['code']=='SOURCE_SELECTION_CHANGED' and count(ready)==0


def test_changed_original_bytes_clear_error(ready):
    pin=setup_pin(ready);t,r,*_=ready
    (t.app.state.settings.blob_dir/CASE/r['evidence']['relativePath']).write_bytes(b'changed')
    with pytest.raises(HTTPException) as e:append(ready,[pin])
    assert e.value.detail['code']=='SOURCE_SELECTION_CHANGED' and count(ready)==0


def test_http_clear_409_not_hash_leak(ready):
    pin=setup_pin(ready);pin['sourceSha256']='0'*64;t,r,_,token,i=ready
    with trial(t) as api:response=api.post(f'/api/v1/trial/cases/{CASE}/issues',headers=headers(token),json={'issueId':i,'operationId':str(uuid.uuid4()),'entry':{'kind':'judgment','note':'test','sourceIds':[r['evidenceId']]},'sourcePins':[pin]})
    assert response.status_code==409 and response.json()=={'code':'SOURCE_SELECTION_CHANGED'} and count(ready)==0


def test_host_discover_pin_save_read(ready):
    async def run():
        async with client(ready) as c:
            sources=await c.dispatch(message(c));pin={k:sources['body']['items'][0][k] for k in ('evidenceId','sourceIncarnation','sourceSha256')}
            req=request(c,ready,entry={'kind':'judgment','note':'test','sourceIds':[pin['evidenceId']]})
            assert not (await c.dispatch(req))['ok'] and count(ready)==0
            req['sourcePins']=[{**pin,'sourceSha256':'0'*64}]
            result=await c.dispatch(req);assert result['code']=='ISSUE_SOURCE_SELECTION_CHANGED' and result['status']==409 and count(ready)==0
            req['sourcePins']=[pin];assert (await c.dispatch(req))['ok'] and count(ready)==1
    asyncio.run(run())


def test_concurrent_same_pinned_operation_once(ready):
    from concurrent.futures import ThreadPoolExecutor
    pin=setup_pin(ready);op=str(uuid.uuid4())
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(lambda _:append(ready,[pin],op),range(2)))
    assert sorted(x['replayed'] for x in results)==[False,True] and count(ready)==1


def test_pin_permission_failure_not_selection_changed(ready,monkeypatch):
    pin=setup_pin(ready)
    def denied(*args):raise HTTPException(403,detail={'code':'DENIED'})
    monkeypatch.setattr(j,'source_current',denied)
    with pytest.raises(HTTPException) as e:append(ready,[pin])
    assert e.value.status_code==403 and count(ready)==0
