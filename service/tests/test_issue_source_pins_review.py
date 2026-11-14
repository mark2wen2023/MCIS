"""Independent review of pin binding, replay and transaction rollback."""
import asyncio,uuid
import pytest
from sqlalchemy import select
from .test_issue_journal import ready
from .test_issue_host_sources import client,message
from .test_issue_host_bridge import request
from .conftest import CASE
from mcis_service.investigation import journal as j

@pytest.mark.parametrize('change',['sha','generation','final-race','none'])
def test_pinned_host_matches_selected_version_and_rolls_back(ready,monkeypatch,change):
 async def run():
  t,r,_,token,i=ready
  async with client(ready) as c:
   listing=await c.dispatch(message(c));item=next(x for x in listing['body']['items'] if x['evidenceId']==r['evidenceId'])
   pins=[{k:item[k] for k in ('evidenceId','sourceIncarnation','sourceSha256')}]
   if change=='sha':pins[0]['sourceSha256']='0'*64
   if change=='generation':pins[0]['sourceIncarnation']=str(uuid.uuid4())
   if change=='final-race':
    original=j.source_current;calls=0
    def changed(*a):
     nonlocal calls
     calls+=1;value=original(*a)
     return {**value,'incarnation':str(uuid.uuid4())} if calls==2 else value
    monkeypatch.setattr(j,'source_current',changed)
   command=request(c,ready,sourcePins=pins,entry={'kind':'judgment','note':'按选中版本','sourceIds':[item['evidenceId']]})
   result=await c.dispatch(command)
   assert result['ok']==(change=='none')
   if change!='none':assert result['code']=='ISSUE_SOURCE_SELECTION_CHANGED' and result['status']==409
   with t.app.state.db.session() as s:
    rows=list(s.scalars(select(j.Event)));assert len(rows)==(1 if change=='none' else 0)
    if rows:
     snapshot=rows[0].doc['sourceSnapshots'][0]
     assert (snapshot['incarnation'],snapshot['sourceSha256'])==(item['sourceIncarnation'],item['sourceSha256'])
 asyncio.run(run())

def test_pinned_replay_retains_original_success_after_source_change(ready):
 async def run():
  t,r,_,token,i=ready
  async with client(ready) as c:
   item=(await c.dispatch(message(c)))['body']['items'][0]
   pin={k:item[k] for k in ('evidenceId','sourceIncarnation','sourceSha256')}
   command=request(c,ready,sourcePins=[pin],entry={'kind':'judgment','note':'原操作','sourceIds':[item['evidenceId']]})
   assert (await c.dispatch(command))['ok']
   (t.app.state.settings.blob_dir/CASE/r['evidence']['relativePath']).write_bytes(b'changed')
   assert (await c.dispatch(command))['ok']
   command['sourcePins'][0]['sourceSha256']='0'*64
   result=await c.dispatch(command);assert not result['ok'] and result['code']!='ISSUE_SOURCE_SELECTION_CHANGED'
   with t.app.state.db.session() as s:assert len(list(s.scalars(select(j.Event))))==1
 asyncio.run(run())
