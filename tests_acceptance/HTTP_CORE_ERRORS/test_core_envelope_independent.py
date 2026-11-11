"""Independent envelope validation: actual HTTP application, synthetic process output."""
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from mcis_service.colreg import core_client
from mcis_service.main import create_app
from mcis_service.config import Settings

MARKER='synthetic-private-marker-only'

@pytest.fixture
def http(tmp_path):
    app=create_app(Settings(data_dir=tmp_path,db_url=f'sqlite:///{tmp_path / "fresh.db"}',seed_demo=False,core_cmd='/synthetic'))
    with TestClient(app,raise_server_exceptions=False) as client:yield client

@pytest.mark.parametrize('env',[
    None,[],False,'text',{},
    {'ok':0},{'ok':1},{'ok':'false'},
    {'ok':False},{'ok':False,'error':None},{'ok':False,'error':[]},
    {'ok':False,'error':{'code':[]}},{'ok':False,'error':{'code':False}},
    {'ok':False,'error':{'code':'BAD_REQUEST','message':{'secret':MARKER}}},
    {'ok':True},{'ok':True,'result':[]},{'ok':True,'result':MARKER},
])
def test_malformed_envelopes_are_502_not_500(http,env):
    with patch.object(core_client.subprocess,'run',return_value=SimpleNamespace(stdout=json.dumps(env).encode(),stderr=MARKER.encode(),returncode=1)):
        response=http.post('/api/v1/core/align',json={})
    assert response.status_code==502
    assert response.json()=={'code':'CORE_BAD_OUTPUT','message':'计算核心返回无效结果。'}
    assert MARKER not in response.text

@pytest.mark.parametrize('error,code,message',[
    ({},'CORE_ERROR',''),
    ({'message':'domain note'},'CORE_ERROR','domain note'),
    ({'code':'BAD_REQUEST'},'BAD_REQUEST',''),
    ({'code':'','message':''},'',''),
])
def test_dictionary_error_defaults_preserved(error,code,message):
    env={'ok':False,'error':error,'result':None,'unknown':MARKER}
    with patch.object(core_client.subprocess,'run',return_value=SimpleNamespace(stdout=json.dumps(env).encode(),stderr=b'',returncode=4)):
        with pytest.raises(core_client.CoreError) as exc:
            core_client.run('/synthetic','align',{})
    assert exc.value.code==code
    assert exc.value.message==message
    assert exc.value.http_status==(422 if code=='BAD_REQUEST' else 502)


def test_last_line_valid_envelope_and_extra_fields_preserved():
    env={'ok':True,'result':{'nested':[1,True,None]},'extension':MARKER,'command':'version','coreVersion':'test'}
    stdout=b'build preamble\n'+json.dumps(env).encode()+b'\n'
    with patch.object(core_client.subprocess,'run',return_value=SimpleNamespace(stdout=stdout,stderr=b'',returncode=0)):
        assert core_client.run('/synthetic','version',{})==env
