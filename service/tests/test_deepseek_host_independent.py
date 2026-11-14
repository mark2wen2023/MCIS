import copy
import json
import pytest
from fastapi import HTTPException
from sqlalchemy import select,text
from .test_host_extraction import extraction_case
from .test_agents_w20 import ITEM
from mcis_service.agents import deepseek_host as r, deepseek_client as d
from mcis_service.identity import local
from mcis_service.interviews.models import InterviewRow

CFG=d.DeepSeekConfig('independent-fictional-key')

def mutate_record(args):
    with args[0].session() as s:
        row=s.scalars(select(InterviewRow).where(InterviewRow.case_id==args[3],InterviewRow.key==args[4])).one()
        doc=copy.deepcopy(row.doc)
        doc['turns'][0]['answer']+=' 后续补充。'
        row.doc=doc

@pytest.mark.parametrize('when',['before','during'])
def test_source_change_invalidates_approval(extraction_case,monkeypatch,when):
    args,_=extraction_case
    approval=r.describe_egress(*args,CFG)['approvalDigest']
    calls=[]
    def infer(*a):
        calls.append(1)
        if when=='during':mutate_record(args)
        return json.dumps({'statements':[ITEM]})
    monkeypatch.setattr(d,'complete',infer)
    if when=='before':mutate_record(args)
    with pytest.raises(HTTPException) as e:
        r.run(*args,CFG,approved_disclosure_digest=approval)
    assert e.value.status_code==409
    assert len(calls)==(when=='during')

def test_approval_not_transferable_to_another_valid_session(extraction_case,monkeypatch):
    args,_=extraction_case
    approval=r.describe_egress(*args,CFG)['approvalDigest']
    with args[0].session() as s:
        subject=local.create_subject(s)
        token=local.issue_session(s,subject)
        local.set_membership(s,subject,args[3],role='LeadInvestigator')
    other=(*args[:2],token,*args[3:])
    monkeypatch.setattr(d,'complete',lambda *a:pytest.fail('no egress'))
    with pytest.raises(HTTPException) as e:
        r.run(*other,CFG,approved_disclosure_digest=approval)
    assert e.value.status_code==409

@pytest.mark.parametrize('content',[
    json.dumps({'statements':[{**ITEM,'quote':'FABRICATED_QUOTE'}]}),
    '{"statements":[],"statements":[]}',
    'SECRET_ERROR_BODY',
    '\ud800',
])
def test_malicious_output_rejected_without_echo(extraction_case,monkeypatch,content):
    args,_=extraction_case
    approval=r.describe_egress(*args,CFG)['approvalDigest']
    monkeypatch.setattr(d,'complete',lambda *a:content)
    with pytest.raises(HTTPException) as e:
        r.run(*args,CFG,approved_disclosure_digest=approval)
    assert e.value.status_code==502
    assert 'SECRET_ERROR_BODY' not in str(e.value)
    assert 'FABRICATED_QUOTE' not in str(e.value)

def test_success_is_pending_not_persistent(extraction_case,monkeypatch):
    args,_=extraction_case
    def counts():
        with args[0].engine.connect() as c:
            return {name:c.execute(text('select count(*) from "'+name+'"')).scalar() for name in c.execute(text("select name from sqlite_master where type='table'")).scalars()}
    before=counts()
    approval=r.describe_egress(*args,CFG)['approvalDigest']
    monkeypatch.setattr(d,'complete',lambda *a:json.dumps({'statements':[ITEM]}))
    result=r.run(*args,CFG,approved_disclosure_digest=approval)
    assert result['status']=='PendingReview'
    assert result['saved'] is False
    assert result['receipt']['humanApprovalVerified'] is False
    assert result['receipt']['persistentAudit'] is False
    assert counts()==before
    assert args[2] not in json.dumps(result)
    assert CFG.api_key not in json.dumps(result)
