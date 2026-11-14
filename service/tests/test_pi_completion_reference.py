import copy,json,uuid
import pytest
from fastapi import HTTPException
from .test_host_extraction import extraction_case
from .test_extraction_working_store import working
from .test_pi_remote import CFG,CONTENT,QUOTE,response,tool,request
from mcis_service.agents import pi_transcript_remote as r,pi_deepseek_transport as t,extraction_working_store as w
from mcis_service.agents.pi_working_host import PiWorkingHost

def new(case,working=False):
 args,_=case;d=r.describe_remote(*args,CFG,completion_mode='validated-reference')
 cls=PiWorkingHost if working else r.RemoteTranscriptHost
 return cls(*args,CFG,approved_disclosure_digest=d['approvalDigest'],completion_mode='validated-reference')
def drive(host,monkeypatch,terminal=r.COMPLETION_MARKER):
 responses=[response([tool('read','find_transcript_passages',{'query':QUOTE})]),response([tool('valid','validate_extraction_proposal',{'content':CONTENT})]),{'finish_reason':'stop','message':{'role':'assistant','content':terminal}}]
 monkeypatch.setattr(t,'complete',lambda *a,**kw:responses.pop(0))
 request(host);host.dispatch({'op':'tool','name':'find_transcript_passages','args':{'query':QUOTE},'callId':'read'})
 request(host);host.dispatch({'op':'tool','name':'validate_extraction_proposal','args':{'content':CONTENT},'callId':'valid'})
 request(host)

def test_reference_uses_host_owned_json_and_working_revalidates(working,monkeypatch):
 host=new(working,True);drive(host,monkeypatch)
 result=host.dispatch({'op':'final','payload':r.COMPLETION_MARKER})
 assert result['completionMode']=='validated-reference' and result['proposals']
 result['proposals'].clear();saved=host.save(str(uuid.uuid4()))
 assert saved['proposal']['result']['proposals'] and not saved['factActivated']
 assert saved['proposal']['result']['execution']['completionMode']=='validated-reference'
 host.close()

@pytest.mark.parametrize('terminal',[CONTENT,r.COMPLETION_MARKER+' ',json.dumps(r.COMPLETION_MARKER),r.COMPLETION_MARKER+'\nother'])
def test_reference_refuses_any_other_final(extraction_case,monkeypatch,terminal):
 host=new(extraction_case);drive(host,monkeypatch,terminal)
 with pytest.raises(HTTPException):host.dispatch({'op':'final','payload':terminal})
 assert host._accepted_content is None

def test_mode_in_approval_digest(extraction_case):
 a,_=extraction_case;d=r.describe_remote(*a,CFG)
 with pytest.raises(HTTPException):r.RemoteTranscriptHost(*a,CFG,approved_disclosure_digest=d['approvalDigest'],completion_mode='validated-reference')
