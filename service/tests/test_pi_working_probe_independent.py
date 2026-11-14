"""Offline scripted probe lifecycle tests; no real provider or human review."""
import asyncio,copy,json,uuid
from pathlib import Path
import pytest
from fastapi import HTTPException
from .test_pi_working_host import accepted
from .test_extraction_working_store import working
from .test_host_extraction import extraction_case
from mcis_service.agents import pi_remote_public_probe as p,pi_deepseek_transport as transport,extraction_review_fixture as fixture
from mcis_service.agents import extraction_working_store as w


def test_independent_working_rehearsal_marks_script_and_preserves_original(working,monkeypatch):
    a,_=working;h,result=accepted(working,monkeypatch);seen=[];real_append=w.append_review
    def append(*args):
        seen.extend(copy.deepcopy(args[-1]));return real_append(*args)
    monkeypatch.setattr(w,'append_review',append)
    outcome=p.working_acceptance(h,a,result)
    assert outcome=={'workingSaved':True,'reopenedRead':True,'reviewRevision':1,'reviewActor':'scripted_test_not_human','factActivated':False,'persistentDuringProbe':True,'storage':'temporary_sqlite_deleted_after_probe'}
    assert seen and all(d['decision']=='needs_verification' and '非人工判断' in d['note'] for d in seen)
    with pytest.raises(ValueError):h.save(str(uuid.uuid4()))
    assert a[2] not in json.dumps(outcome)


def test_independent_working_rehearsal_failure_never_reports_success(working,monkeypatch):
    a,_=working;h,result=accepted(working,monkeypatch)
    monkeypatch.setattr(w,'append_review',lambda *a: (_ for _ in ()).throw(HTTPException(403,'script denied')))
    with pytest.raises(HTTPException):p.working_acceptance(h,a,result)
    records=w.list_records(*a[:4]);assert len(records['items'])==1
    assert w.read(*a[:4],records['items'][0]['proposalId'])['revision']==0


@pytest.mark.parametrize('working_mode',[False,True])
def test_independent_probe_final_receipt_after_temporary_cleanup(working_mode,monkeypatch):
    content=fixture.fixture_content();terminal='MCIS_COMPLETE_VALIDATED_PROPOSAL' if working_mode else content;query='右满舵';roots=[];outputs=[];actual_temp=p.tempfile.TemporaryDirectory
    def temp(*args,**kwargs):
        value=actual_temp(*args,**kwargs);roots.append(Path(value.name));return value
    monkeypatch.setattr(p.tempfile,'TemporaryDirectory',temp)
    monkeypatch.setattr(p,'public_document',fixture.document)
    def tool(callid,name,args):return {'id':callid,'type':'function','function':{'name':name,'arguments':json.dumps(args)}}
    calls=[tool('read','find_transcript_passages',{'query':query}),tool('validate','validate_extraction_proposal',{'content':content})]
    responses=[{'finish_reason':'tool_calls','message':{'role':'assistant','content':None,'tool_calls':[x]}} for x in calls]+[{'finish_reason':'stop','message':{'role':'assistant','content':terminal}}]
    def complete(*args,**kwargs):return responses.pop(0)
    monkeypatch.setattr(transport,'complete',complete)
    messages=[{'apiKey':'fake-offline-only'}]
    for c in calls:
        messages.extend([{'op':'model_start'},{'op':'model_request'},{'op':'model_end'},{'op':'tool','name':c['function']['name'],'args':json.loads(c['function']['arguments']),'callId':c['id']}])
    messages.extend([{'op':'model_start'},{'op':'model_request'},{'op':'model_end'},{'op':'final','payload':terminal}])
    class Lines:
        def read(self,*args):return json.dumps(messages.pop(0)).encode() if messages else None
    monkeypatch.setattr(p,'Lines',Lines)
    def output(value):
        outputs.append(copy.deepcopy(value))
        if value.get('providerMode')=='remote-deepseek':assert all(not root.exists() for root in roots)
    monkeypatch.setattr(p,'output',output)
    asyncio.run(p.run(working_mode));assert not messages and not responses
    final=outputs[-1];assert final['providerMode']=='remote-deepseek' and final['saved'] is False
    if working_mode:
        assert final['workingAcceptance']['reviewActor']=='scripted_test_not_human'
        assert final['workingAcceptance']['reviewRevision']==1
    else:assert 'workingAcceptance' not in final
    assert all(not root.exists() for root in roots)
    assert 'fake-offline-only' not in json.dumps(outputs)
    assert {x['function']['name'] for x in transport.TOOL_SCHEMAS}=={'read_transcript_excerpt','find_transcript_passages','validate_extraction_proposal'}
