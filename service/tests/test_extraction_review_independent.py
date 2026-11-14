"""Independent review of the ephemeral review boundary; fictional providers only."""
import asyncio,copy,json,subprocess,sys
import pytest
from sqlalchemy import select
from .test_host_extraction import extraction_case
from .test_extraction_review_host import make,request,decision
from mcis_service.db import get_doc,put_doc
from mcis_service.interviews.models import InterviewRow
from mcis_service.agents.models import AgentDraftRow
from mcis_service.identity import local

@pytest.mark.parametrize('change',['record','policy','member'])
def test_generation_binding_must_still_hold_at_human_review(extraction_case,change):
 async def run():
  args,_=extraction_case;db,settings,token,case,record=args
  async with make(extraction_case) as host:
   proposal=(await host.dispatch(request(host)))['body']['proposalId']
   with db.session() as s:
    if change=='record':
     doc=copy.deepcopy(get_doc(s,InterviewRow,case,record));doc['turns'][0]['answer']+='新证据改变笔录';put_doc(s,InterviewRow,case,record,doc)
    elif change=='policy':
     from mcis_service.redaction.gateway import get_policy
     from mcis_service.redaction.models import AccessPolicyRow
     policy=copy.deepcopy(get_policy(s,case));policy['matrix']['AgentService']['testimony']='Deny';put_doc(s,AccessPolicyRow,case,'policy',policy)
    else:
     subject=local.authorize_read(s,token,case).subject_id
     local.set_membership(s,subject,case,role='LeadInvestigator',enabled=False)
   result=await host.dispatch(request(host,'review',proposalId=proposal,decisions=decision()))
   assert not result['ok'] and 'body' not in result and token not in str(result)
   with db.session() as s:
    assert get_doc(s,InterviewRow,case,record)['statements']==[]
    assert not list(s.scalars(select(AgentDraftRow)))
 asyncio.run(run())

def test_original_review_cached_is_immutable_and_not_persisted(extraction_case):
 async def run():
  args,_=extraction_case
  async with make(extraction_case) as host:
   pid=(await host.dispatch(request(host)))['body']['proposalId']
   req=request(host,'review',proposalId=pid,decisions=decision());first=await host.dispatch(req)
   first['body']['decisions'][0]['note']='tamper'
   again=await host.dispatch(req);assert again['body']['decisions']==decision()
   assert again['body']['saved'] is False and again['body']['factVerified'] is False
   with args[0].session() as s:
    assert not list(s.scalars(select(AgentDraftRow)))
    assert get_doc(s,InterviewRow,args[3],args[4])['statements']==[]
 asyncio.run(run())

def test_fixture_real_subprocess_bounded_protocol():
 process=subprocess.Popen([sys.executable,'-m','mcis_service.agents.extraction_review_fixture'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 try:
  scope=json.loads(process.stdout.readline());assert scope['fixture']=='fictional-fixed-output'
  import uuid
  base={k:scope[k] for k in ('profile','contextId','caseId','recordId')}
  gen={**base,'requestId':str(uuid.uuid4()),'action':'generate'}
  def ask(value):
   process.stdin.write(json.dumps(value)+'\n');process.stdin.flush();return json.loads(process.stdout.readline())
  result=ask(gen);assert result['ok'];b=result['body'];assert b['fixture'] and not b['inferencePerformed'] and len(b['proposals'])==2
  review={**base,'requestId':str(uuid.uuid4()),'action':'review','proposalId':b['proposalId'],'decisions':[{'index':i,'decision':'needs_verification','note':'需补充原件核验'} for i in (1,2)]}
  saved=ask(review);assert saved['ok'] and saved['body']['saved'] is False and saved['body']['factVerified'] is False
  assert ask(review)==saved
  process.stdin.close();assert process.wait(timeout=10)==0;assert process.stderr.read()==''
 finally:
  if process.poll() is None:process.kill();process.wait()
