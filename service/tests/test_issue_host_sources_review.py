"""Independent integration review: actual catalog then source-bearing journal write."""
import asyncio
import pytest
from .test_issue_journal import ready
from .test_issue_host_sources import client,message
from .test_issue_host_bridge import request
from .conftest import CASE
from mcis_service.investigation import journal
from mcis_service.identity import local

@pytest.mark.parametrize('change',['none','bytes','member','grant','missing'])
def test_catalog_selection_save_rechecks_actual_source_and_authority(ready,change):
 async def run():
  t,r,subject,token,issue=ready
  async with client(ready) as c:
   listing=await c.dispatch(message(c));assert listing['ok']
   source=r['evidenceId'];assert source in [x['evidenceId'] for x in listing['body']['items']]
   if change=='bytes':(t.app.state.settings.blob_dir/CASE/r['evidence']['relativePath']).write_bytes(b'changed after discovery')
   if change=='member':
    with t.app.state.db.session() as s:local.set_membership(s,subject,CASE,role='LeadInvestigator',enabled=False)
   if change=='grant':
    with t.app.state.db.session() as s:journal.grant(s,subject,CASE,enabled=False)
   if change=='missing':source='missing-source'
   selected=next(x for x in listing['body']['items'] if x['evidenceId']==r['evidenceId'])
   pin={k:selected[k] for k in ('evidenceId','sourceIncarnation','sourceSha256')}
   if change=='missing':pin['evidenceId']=source
   saved=await c.dispatch(request(c,ready,sourcePins=[pin],entry={'kind':'judgment','note':'来源辅助初判，未审核','sourceIds':[source]}))
   assert saved['ok']==(change=='none')
   if change=='none':
    assert saved['body']['events'][0]['sourceIds']==[source]
    actual=journal.read(t.app.state.db,token,CASE,issue)
    assert actual['events'][0]['sourceSnapshots'][0]['evidenceId']==source
    assert 'sourceSnapshots' not in saved['body']['events'][0]
   with t.app.state.db.session() as s:
    from sqlalchemy import select
    assert len(list(s.scalars(select(journal.Event))))==(1 if change=='none' else 0)
 asyncio.run(run())
