"""Fixed synthetic stdio test controls only; never an application endpoint."""
import asyncio,json,sys,tempfile,uuid,os
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,os.environ['MCIS_HOST_SERVICE'])
from sqlalchemy import select
from mcis_service.config import Settings
from mcis_service.db import Database
from mcis_service.identity.demo import prepare,CASE
from mcis_service.identity.local import authorize_read,set_membership,create_subject,issue_session
from mcis_service.investigation import journal
from mcis_service.investigation.host_bridge import IssueHostClient
from mcis_service.evidence.models import EvidenceRow
from mcis_service.evidence_intake.incarnation import SourceIncarnationRow
from mcis_service.evidence_intake.router import file_path
async def run():
 with tempfile.TemporaryDirectory(prefix='w3-ui-version-') as directory:
  root=Path(directory);settings=Settings(data_dir=root,db_url=f'sqlite:///{root/"test.db"}',seed_demo=False,core_cmd='unused',host='127.0.0.1',port=0)
  settings.blob_dir.mkdir(parents=True);db=Database(settings.resolved_db_url);host=None
  try:
   db.create_all();journal.initialize(db);token=await prepare(db,settings)
   with db.session() as s:
    subject=authorize_read(s,token,CASE).subject_id;journal.grant(s,subject,CASE,enabled=True)
   with db.session() as s:
    other=create_subject(s);other_token=issue_session(s,other,lifetime_seconds=300);set_membership(s,other,CASE,role='LeadInvestigator',can_save_unreviewed=True);journal.grant(s,other,CASE,enabled=True)
   host=IssueHostClient(db=db,settings=settings,session_token=token,case_id=CASE)
   def request(action,**kw):return {k:v for k,v in {**host.scope,'requestId':str(uuid.uuid4()),'action':action,**kw}.items() if k!='productionLogin'}
   sources=(await host.dispatch(request('sources')))['body']['items'];ids=[str(uuid.uuid4()),str(uuid.uuid4())]
   for i,item in enumerate(sources):
    result=await host.dispatch(request('save',issueId=ids[i],operationId=str(uuid.uuid4()),expectedRevision=0,entry={'kind':'judgment','note':['假设甲待核','假设乙待核'][i],'sourceIds':[item['evidenceId']]},sourcePins=[{k:item[k] for k in ('evidenceId','sourceIncarnation','sourceSha256')}]))
    assert result['ok']
   with db.session() as s:
    row=s.scalars(select(EvidenceRow).where(EvidenceRow.case_id==CASE,EvidenceRow.key==sources[0]['evidenceId'])).one();target=file_path(SimpleNamespace(settings=settings),CASE,row.doc['relativePath'])
   original=target.read_bytes()
   def output(x):print(json.dumps(x,ensure_ascii=False),flush=True)
   output({'scope':host.scope,'ids':ids})
   for line in sys.stdin:
    value=json.loads(line)
    if value in ({'testControl':'other-judgment'},{'testControl':'other-verification'}):
     async with IssueHostClient(db=db,settings=settings,session_token=other_token,case_id=CASE) as other_host:
      def other_request(action,**kw):return {k:v for k,v in {**other_host.scope,'requestId':str(uuid.uuid4()),'action':action,**kw}.items() if k!='productionLogin'}
      prior=(await other_host.dispatch(other_request('read',issueId=ids[1])))['body']
      latest=max(e['seq'] for e in prior['events'] if e['kind']=='judgment')
      verification=value['testControl']=='other-verification'
      result=await other_host.dispatch(other_request('save',issueId=ids[1],operationId=str(uuid.uuid4()),expectedRevision=prior['revision'],entry={'kind':'verification' if verification else 'judgment','note':'另一虚构调查员核实待定' if verification else '另一虚构调查员新判断','sourceIds':[],'outcome':'inconclusive' if verification else None,'againstJudgment':latest if verification else None}))
      assert result['ok'];output({'ok':True,'revision':result['body']['revision']})
    elif value=={'testControl':'fault'}:
     target.write_bytes(original.replace(b',45',b',46'));output({'ok':True})
    elif value=={'testControl':'reopen'}:
     await host.__aexit__(None,None,None);db.engine.dispose();db=Database(settings.resolved_db_url)
     host=IssueHostClient(db=db,settings=settings,session_token=token,case_id=CASE);output({'scope':host.scope,'ids':ids})
    elif value=={'testControl':'unavailable'}:
     with db.session() as s:s.delete(s.get(SourceIncarnationRow,(CASE,sources[0]['evidenceId'])))
     output({'ok':True})
    elif value=={'testControl':'restore-membership'}:
     with db.session() as s:set_membership(s,subject,CASE,role='LeadInvestigator',enabled=True,can_save_unreviewed=True)
     output({'ok':True})
    elif value=={'testControl':'revoke'}:
     with db.session() as s:set_membership(s,subject,CASE,role='LeadInvestigator',enabled=False)
     output({'ok':True})
    else:output(await host.dispatch(value))
  finally:
   if host:await host.__aexit__(None,None,None)
   db.engine.dispose()
asyncio.run(run())
