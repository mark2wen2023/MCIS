import json
import pytest
from mcis_service.agents import deepseek_probe as p, deepseek_client as d
from mcis_service.agents.extraction_review_fixture import fixture_content

def test_no_implicit_credential_read(monkeypatch):
    def forbidden(): raise AssertionError('should not access config')
    monkeypatch.setattr(d,'config_from_environment',forbidden)
    assert p.run_probe()['status']=='not_requested'

def test_no_key(monkeypatch):
    monkeypatch.delenv('DEEPSEEK_API_KEY',raising=False)
    assert p.run_probe(send_fictional=True)['status']=='not_connected'

def test_mock_inference_checked(monkeypatch):
    monkeypatch.setattr(d,'config_from_environment',lambda:d.DeepSeekConfig('synthetic-key'))
    def complete(cfg,messages):
        assert '我声称右满舵避让' in messages[1]['content']
        return fixture_content()
    monkeypatch.setattr(d,'complete',complete)
    result=p.run_probe(send_fictional=True)
    assert result['status']=='validated_response'
    assert result['proposalCount']==2
    assert result['protectedHostIntegrated'] is False
    assert result['saved'] is False

@pytest.mark.parametrize('content',['{}','not json',fixture_content().replace('右满舵避让','不存在的事实')])
def test_invalid_or_fabricated_output(monkeypatch,content):
    monkeypatch.setattr(d,'config_from_environment',lambda:d.DeepSeekConfig('synthetic-key'))
    monkeypatch.setattr(d,'complete',lambda *a:content)
    assert p.run_probe(send_fictional=True)['status']=='unconfirmed'

def test_cli_never_accepts_case_or_key(capsys):
    assert p.main(['--api-key','secret'])==2
    assert 'secret' not in capsys.readouterr().out
