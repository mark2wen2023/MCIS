"""Mock transport success/failure are contract checks, not real-model evidence."""
import json,os,subprocess,sys
import pytest
from mcis_service.agents import local_extraction_probe as p,model_client as m
from mcis_service.agents.extraction_review_fixture import fixture_content


def test_no_config_no_transport_even_env(monkeypatch):
    monkeypatch.setenv('MCIS_AGENT_BASE_URL','http://127.0.0.1:9999/v1')
    monkeypatch.setenv('MCIS_AGENT_MODEL','do-not-use')
    monkeypatch.setattr(m,'complete',lambda *_:pytest.fail('network attempted'))
    result=p.run_probe();assert result['status']=='not_connected' and not result['requestAttempted']

@pytest.mark.parametrize('kwargs',[{'model':'x'},{'base_url':'http://127.0.0.1:1/v1'},
    {'base_url':'http://remote:1/v1','model':'x'}, {'base_url':'http://127.0.0.1:1/v1','model':' '}])
def test_invalid_no_call(kwargs,monkeypatch):
    monkeypatch.setattr(m,'complete',lambda *_:pytest.fail('network attempted'))
    assert p.run_probe(**kwargs)['status']=='invalid_configuration'


def test_mock_success_is_contract_not_model(monkeypatch):
    seen=[]
    def complete(cfg,messages):seen.append((cfg,messages));return fixture_content()
    monkeypatch.setattr(m,'complete',complete)
    result=p.run_probe(base_url='http://127.0.0.1:9876/v1',model='declared-model')
    assert result['status']=='validated_response' and result['proposalCount']==2 and result['citationCount']==2
    assert len(seen)==1 and result['modelIdentityVerified'] is False and not result['saved']
    assert result['configuredModel']=='declared-model' and 'messages' not in result and 'proposals' not in result
    assert result['sourceScope']=='interview_document_only' and not result['fixtureFallback']


def test_mock_error_sanitized_and_no_fallback(monkeypatch):
    def complete(*_):raise RuntimeError('private-token raw prompt')
    monkeypatch.setattr(m,'complete',complete)
    result=p.run_probe(base_url='http://127.0.0.1:9876/v1',model='declared')
    assert result['status']=='unconfirmed' and result['endpointConfigured'] and result['requestAttempted'] is None
    assert 'private' not in json.dumps(result) and not result['fixtureFallback']


def test_real_subprocess_default_and_badargs_no_network():
    env=dict(os.environ,PYTHONPATH='issue-journal/service')
    for args,status,code in [([], 'not_connected',0),(['--secret','do-not-echo'], 'invalid_configuration',2)]:
        result=subprocess.run([sys.executable,'-m','mcis_service.agents.local_extraction_probe',*args],capture_output=True,text=True,env=env,timeout=15)
        assert result.returncode==code and json.loads(result.stdout)['status']==status
        assert 'do-not-echo' not in result.stdout+result.stderr
