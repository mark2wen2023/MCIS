"""Actual protected ASGI/SQLite path; synthetic file mutation is fault injection."""
import asyncio,json,sys,tempfile,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent/'service'))
from sqlalchemy import select,text,inspect
from mcis_service.config import Settings
from mcis_service.db import Database
from mcis_service.identity.demo import prepare,CASE
from mcis_service.identity.local import authorize_read,set_membership
from mcis_service.investigation import journal
from mcis_service.investigation.host_bridge import IssueHostClient
from mcis_service.evidence.models import EvidenceRow
from mcis_service.evidence_intake.incarnation import SourceIncarnationRow
from mcis_service.evidence_intake.router import file_path

def uid():return str(uuid.uuid4())
async def run():
 checks=[]
 with tempfile.TemporaryDirectory(prefix='w3-version-states-') as directory:
  root=Path(directory);settings=Settings(data_dir=root,db_url=f'sqlite:///{root/"test.db"}',seed_demo=False,core_cmd='unused',host='127.0.0.1',port=0)
  settings.blob_dir.mkdir(parents=True);db=Database(settings.resolved_db_url)
  try:
   db.create_all();journal.initialize(db);token=await prepare(db,settings)
   with db.session() as s:
    subject=authorize_read(s,token,CASE).subject_id;journal.grant(s,subject,CASE,enabled=True)
   ids=[uid(),uid()]
   async with IssueHostClient(db=db,settings=settings,session_token=token,case_id=CASE) as host:
    async def call(action,**kw):
     return await host.dispatch({k:v for k,v in {**host.scope,'requestId':uid(),'action':action,**kw}.items() if k!='productionLogin'})
    sources=(await call('sources'))['body']['items']
    for i,source in enumerate(sources):
     pin={k:source[k] for k in ('evidenceId','sourceIncarnation','sourceSha256')}
     r=await call('save',issueId=ids[i],operationId=uid(),expectedRevision=0,entry={'kind':'judgment','note':['假设甲待核','假设乙待核'][i],'sourceIds':[pin['evidenceId']]},sourcePins=[pin]);assert r['ok']
    # Two further real journal appends reuse card A's source (three references).
    for revision in (1,2):
     pin={k:sources[0][k] for k in ('evidenceId','sourceIncarnation','sourceSha256')}
     result=await call('save',issueId=ids[0],operationId=uid(),expectedRevision=revision,entry={'kind':'judgment','note':'保留待核判断 '+str(revision),'sourceIds':[pin['evidenceId']]},sourcePins=[pin]);assert result['ok']
    original_check=journal.source_current
    with patch.object(journal,'source_current',wraps=original_check) as counted:
     for expected in (1,2):
      result=await call('read',issueId=ids[0]);assert result['ok'] and len(result['body']['events'])==3
      assert counted.call_count==expected
    checks.append('three_references_one_real_check_each_request')
    with db.engine.connect() as connection:
     counts={name:connection.execute(text('SELECT COUNT(*) FROM "'+name+'"')).scalar() for name in inspect(db.engine).get_table_names()}
    initial=[(await call('read',issueId=i))['body'] for i in ids]
    def state(body):return body['events'][0]['sourceVersionStates'][0]
    assert all(state(b)['status']=='current' for b in initial);checks.append('two_current_cards')
    with db.session() as s:
     history=[json.dumps(e.doc,sort_keys=True) for e in s.scalars(select(journal.Event).order_by(journal.Event.issue_id))]
     row=s.scalars(select(EvidenceRow).where(EvidenceRow.case_id==CASE,EvidenceRow.key==sources[0]['evidenceId'])).one()
     target=file_path(SimpleNamespace(settings=settings),CASE,row.doc['relativePath'])
    original=target.read_bytes();assert b',45' in original
    target.write_bytes(original.replace(b',45',b',46')) # local fault injection, NOT registration replacement API
    changed=[(await call('read',issueId=i))['body'] for i in ids]
    assert state(changed[0])['status']=='needs_review' and changed[1]==initial[1];checks.append('actual_byte_change_only_first_affected')
    assert all(set(item)=={'evidenceId','status'} for body in initial+changed for event in body['events'] for item in event['sourceVersionStates']);checks.append('state_projection_no_historical_digest_or_incarnation')
    with patch.object(journal,'source_current',wraps=original_check) as counted:
     bad=await call('read',issueId=ids[0]);assert counted.call_count==1
     assert all(e['sourceVersionStates'][0]['status']=='needs_review' for e in bad['body']['events'])
    checks.append('failed_integrity_checked_once_for_repeated_references')
    wrong_context=await call('read',contextId=uid(),issueId=ids[0]);assert not wrong_context['ok'] and 'body' not in wrong_context;checks.append('context_switch_no_history')
    foreign=await call('read',caseId='FOREIGN',issueId=ids[0]);assert not foreign['ok'] and 'body' not in foreign;checks.append('cross_case_no_history')
   db.engine.dispose();db=Database(settings.resolved_db_url)
   async with IssueHostClient(db=db,settings=settings,session_token=token,case_id=CASE) as host:
    async def call(action,**kw):
     return await host.dispatch({k:v for k,v in {**host.scope,'requestId':uid(),'action':action,**kw}.items() if k!='productionLogin'})
    reopened=[(await call('read',issueId=i))['body'] for i in ids];assert reopened==changed;checks.append('sqlite_reopen')
    # Existing integrity checker cannot distinguish missing bytes from mismatched bytes:
    # both are conservatively needs_review, never current.
    target.unlink();missing=(await call('read',issueId=ids[0]))['body'];assert state(missing)['status']=='needs_review';checks.append('missing_file_not_current')
    target.write_bytes(original)
    restored=(await call('read',issueId=ids[0]))['body'];assert restored==initial[0];checks.append('exact_bytes_restore_not_history_rewrite')
    with db.engine.connect() as connection:
     assert counts=={name:connection.execute(text('SELECT COUNT(*) FROM "'+name+'"')).scalar() for name in inspect(db.engine).get_table_names()};checks.append('reads_no_table_or_audit_writes')
    with db.session() as s:
     row=s.get(SourceIncarnationRow,(CASE,sources[0]['evidenceId']));s.delete(row)
    unavailable=(await call('read',issueId=ids[0]))['body'];assert state(unavailable)['status']=='unavailable';checks.append('missing_registered_identity_unavailable')
    assert (await call('read',issueId=ids[1]))['body']==initial[1]
    with db.session() as s:set_membership(s,subject,CASE,role='LeadInvestigator',enabled=False)
    denied=await call('read',issueId=ids[0]);assert not denied['ok'] and 'body' not in denied;checks.append('revocation_no_history_or_digest')
    with db.session() as s:
     assert history==[json.dumps(e.doc,sort_keys=True) for e in s.scalars(select(journal.Event).order_by(journal.Event.issue_id))];checks.append('journal_unchanged')
   print(json.dumps({'passed':len(checks),'checks':checks,'replacement':'temporary_file_fault_injection_not_product_version_api','browser':False,'model':False}))
  finally:db.engine.dispose()
 assert not root.exists()
asyncio.run(run())
