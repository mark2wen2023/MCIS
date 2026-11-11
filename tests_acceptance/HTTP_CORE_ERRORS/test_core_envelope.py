"""Core output type boundary; synthetic subprocess only."""
import json
from types import SimpleNamespace
import pytest
from mcis_service.colreg import core_client

INVALID=[None,[],1,'text',{}, {'ok':None},{'ok':1},{'ok':'true'},
 {'ok':False,'error':[]},{'ok':False,'error':'text'},
 {'ok':False,'error':{'code':[]}},{'ok':False,'error':{'code':{},'message':'x'}},
 {'ok':False,'error':{'code':'BAD_REQUEST','message':[]}},
 {'ok':True,'result':[]},{'ok':True,'result':None}]

@pytest.mark.parametrize('env',INVALID)
def test_malformed_output_is_core_bad_output(monkeypatch,env):
    monkeypatch.setattr(core_client.subprocess,'run',lambda *a,**kw:SimpleNamespace(stdout=json.dumps(env).encode(),stderr=b'',returncode=0))
    with pytest.raises(core_client.CoreError) as exc:core_client.run('/synthetic','align',{})
    assert exc.value.code=='CORE_BAD_OUTPUT'
    assert exc.value.http_status==502

@pytest.mark.parametrize('command',['cpa','align','version','colreg'])
def test_valid_success_preserves_all_fields(monkeypatch,command):
    env={'ok':True,'command':command,'coreVersion':'test','result':{},'extension':['preserve']}
    monkeypatch.setattr(core_client.subprocess,'run',lambda *a,**kw:SimpleNamespace(stdout=json.dumps(env).encode(),stderr=b'',returncode=0))
    assert core_client.run('/synthetic',command,{})==env

@pytest.mark.parametrize('code,status',[('BAD_JSON',422),('BAD_REQUEST',422),('UNKNOWN_COMMAND',501),('NOT_IMPLEMENTED',501),('custom',502)])
def test_valid_error_preserves_domain_mapping(monkeypatch,code,status):
    env={'ok':False,'error':{'code':code,'message':'domain message'}}
    monkeypatch.setattr(core_client.subprocess,'run',lambda *a,**kw:SimpleNamespace(stdout=json.dumps(env).encode(),stderr=b'',returncode=4))
    with pytest.raises(core_client.CoreError) as exc:core_client.run('/synthetic','align',{})
    assert (exc.value.code,exc.value.http_status,exc.value.message)==(code,status,'domain message')
