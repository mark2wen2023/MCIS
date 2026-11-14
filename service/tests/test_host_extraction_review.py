"""Independent protected-host extraction checks; all providers are fake fixtures."""
import copy,json
import pytest
from fastapi import HTTPException
from .test_agents_w20 import interview,ITEM,RECORD,clean_model_env
from .conftest import CASE
from .test_local_authority import provision
from mcis_service.agents import host_extraction as h
from mcis_service.identity import local
from mcis_service.db import get_doc,put_doc
from mcis_service.interviews.models import InterviewRow
from mcis_service.agents.models import AgentDraftRow
from sqlalchemy import select

@pytest.fixture
def bound(client,empty_client,monkeypatch):
 from .test_internal_unreviewed_save import setup
 target,_,_=setup(client,empty_client,monkeypatch)
 interview.__wrapped__(target)
 subject,token=provision(target);db=target.app.state.db;settings=target.app.state.settings
 return target,subject,token,h.describe(db,settings,token,CASE,RECORD)['bindingDigest']

def call(v,provider=None,**kw):
 client,_,token,digest=v
 return h.run(client.app.state.db,client.app.state.settings,token,CASE,RECORD,kw.get('digest',digest),provider)

@pytest.mark.parametrize('change',['session','record','policy'])
def test_changed_after_model_does_not_release_or_persist(bound,monkeypatch,change):
 client,subject,token,_=bound
 def complete(self,messages):
  assert '13812345678' not in str(messages) and '私人片段' not in str(messages)
  with client.app.state.db.session() as s:
   if change=='session':local.revoke_session(s,token)
   elif change=='record':
    doc=copy.deepcopy(get_doc(s,InterviewRow,CASE,RECORD));doc['turns'][0]['answer']+='后续更正';put_doc(s,InterviewRow,CASE,RECORD,doc)
   else:
    from mcis_service.redaction.gateway import get_policy
    from mcis_service.redaction.models import AccessPolicyRow
    policy=copy.deepcopy(get_policy(s,CASE));policy['matrix']['AgentService']['testimony']='Deny';put_doc(s,AccessPolicyRow,CASE,'policy',policy)
  return json.dumps({'statements':[ITEM]},ensure_ascii=False)
 monkeypatch.setattr(h.FixtureProvider,'complete',complete)
 with pytest.raises(HTTPException) as e:call(bound,h.FixtureProvider('ignored'))
 assert e.value.status_code in (403,409)
 with client.app.state.db.session() as s:
  assert not list(s.scalars(select(AgentDraftRow)))
  assert get_doc(s,InterviewRow,CASE,RECORD)['statements']==[]

def test_default_and_fixed_fixture_not_claimed_real(bound):
 v=call(bound);assert v['status']=='not_connected' and v['proposals']==[] and not v['inferencePerformed']
 v=call(bound,h.FixtureProvider(json.dumps({'statements':[ITEM]},ensure_ascii=False)))
 assert v['status']=='PendingReview' and v['fixture'] and not v['inferencePerformed'] and not v['saved']
 assert v['receipt']['sourceScope']=='interview_document_only' and not v['receipt']['persistentAudit']
 assert v['proposals'][0]['quote']==ITEM['quote'] and v['proposals'][0]['reviewStatus']=='Draft'
 assert bound[2] not in str(v)

@pytest.mark.parametrize('content',['{"statements":[]}','{"statements":[],"statements":[]}','x'*262145])
def test_bad_or_overbudget_no_output(bound,content):
 with pytest.raises(HTTPException) as e:call(bound,h.FixtureProvider(content))
 assert e.value.detail['code']=='HOST_EXTRACTION_FAILED'

def test_stale_binding_prevents_provider_invocation(bound,monkeypatch):
 monkeypatch.setattr(h.FixtureProvider,'complete',lambda *_:pytest.fail('stale binding must not invoke'))
 with pytest.raises(HTTPException) as e:call(bound,h.FixtureProvider('unused'),digest='0'*64)
 assert e.value.status_code==409
