import json
import pytest
from fastapi import HTTPException
from .test_host_extraction import extraction_case
from .test_agents_w20 import ITEM
from mcis_service.agents import deepseek_host as r, deepseek_client as d
from mcis_service.identity import local

CFG=d.DeepSeekConfig('fake-test-key')

def test_default_no_remote_even_env(extraction_case,monkeypatch):
    args,_=extraction_case
    monkeypatch.setenv('DEEPSEEK_API_KEY','fake-test-key')
    monkeypatch.setattr(d,'complete',lambda *a:pytest.fail('unexpected egress'))
    assert r.run(*args)['status']=='not_connected'

@pytest.mark.parametrize('approval',[None,'','x','0'*64])
def test_no_approved_scope_no_egress(extraction_case,monkeypatch,approval):
    args,_=extraction_case
    monkeypatch.setattr(d,'complete',lambda *a:pytest.fail('unexpected egress'))
    with pytest.raises(HTTPException):r.run(*args,CFG,approved_disclosure_digest=approval)

def test_scope_and_redaction(extraction_case,monkeypatch):
    args,_=extraction_case
    disclosure=r.describe_egress(*args,CFG)
    assert disclosure['destination']==d.ENDPOINT
    assert args[2] not in json.dumps(disclosure)
    assert CFG.api_key not in json.dumps(disclosure)
    def complete(cfg,messages):
        text=json.dumps(messages,ensure_ascii=False)
        for secret in ['13812345678','私人片段','测试甲',args[2]]:assert secret not in text
        return json.dumps({'statements':[ITEM]})
    monkeypatch.setattr(d,'complete',complete)
    result=r.run(*args,CFG,approved_disclosure_digest=disclosure['approvalDigest'])
    assert result['status']=='PendingReview' and not result['saved']
    assert result['receipt']['providerMode']=='remote-deepseek'
    assert CFG.api_key not in json.dumps(result)

def test_model_changed_needs_reapproval(extraction_case,monkeypatch):
    args,_=extraction_case;disclosure=r.describe_egress(*args,CFG)
    monkeypatch.setattr(d,'complete',lambda *a:pytest.fail('unexpected egress'))
    with pytest.raises(HTTPException):r.run(*args,d.DeepSeekConfig(CFG.api_key,'deepseek-flash'),approved_disclosure_digest=disclosure['approvalDigest'])

def test_revoked_after_approval(extraction_case,monkeypatch):
    args,_=extraction_case;disclosure=r.describe_egress(*args,CFG)
    with args[0].session() as s:local.revoke_session(s,args[2])
    monkeypatch.setattr(d,'complete',lambda *a:pytest.fail('unexpected egress'))
    with pytest.raises(HTTPException):r.run(*args,CFG,approved_disclosure_digest=disclosure['approvalDigest'])

def test_revoked_during_call_returns_no_result(extraction_case,monkeypatch):
    args,_=extraction_case;disclosure=r.describe_egress(*args,CFG)
    def complete(*a):
        with args[0].session() as s:local.revoke_session(s,args[2])
        return json.dumps({'statements':[ITEM]})
    monkeypatch.setattr(d,'complete',complete)
    with pytest.raises(HTTPException):r.run(*args,CFG,approved_disclosure_digest=disclosure['approvalDigest'])
