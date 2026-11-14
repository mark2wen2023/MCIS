import copy,importlib.util,json,sys,time
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parent))
import blind_host as b

def host():
 c,m=b.project();return b.Host(c,m,fixture=True)

def request(h):
 h.dispatch({'op':'model_start'});event=h.dispatch({'op':'model_request'})
 return h.dispatch({'op':'request_attempt_ack','attempt':event['attempt']})

def tool(h,response):
 h.dispatch({'op':'model_end'});call=response['message']['tool_calls'][0]
 return h.dispatch({'op':'tool','name':call['function']['name'],'args':json.loads(call['function']['arguments']),'callId':call['id']})

def test_complete_fixture():
 h=host();tool(h,request(h));assert tool(h,request(h))['schemaOnly']
 request(h);h.dispatch({'op':'model_end'});r=h.dispatch({'op':'final','payload':b.MARKER})
 assert r['realRequestsStarted']==0 and not r['realModel'] and len(r['predictions']['predictions'])==11
 assert r['predictions']['origin']=='scripted_fixture'
 assert h.dispatch({'op':'close'})['closed']

def test_projection_has_no_answers_or_semantic_ids():
 h=host();raw=json.dumps(h.cases)
 for excluded in ('suggestedLabel','rationale','oil_wrong_vessel','fixture-predictions','provenance'):
  assert excluded not in raw
 assert list(h.mapping)==[f'case_{n:03d}' for n in range(1,12)]

def test_ack_required_and_transport_failure_unknown():
 c,m=b.project();calls=[]
 def fail(*args):calls.append(True);raise TimeoutError()
 h=b.Host(c,m,fixture=False,key='sk-test-not-real-secret',transport=fail)
 h.dispatch({'op':'model_start'});h.dispatch({'op':'model_request'});assert not calls
 with pytest.raises(TimeoutError):h.dispatch({'op':'request_attempt_ack','attempt':1})
 assert h.closed and h.inflight and h.key is None and calls==[True]
 with pytest.raises(ValueError):h.dispatch({'op':'model_start'})
 assert calls==[True]

def test_wrong_ack_closes():
 h=host();h.dispatch({'op':'model_start'});h.dispatch({'op':'model_request'})
 with pytest.raises(ValueError):h.dispatch({'op':'request_attempt_ack','attempt':True})
 assert h.closed

def test_index_and_empty_tool_content():
 h=host();h.models=1;r=h.fixture_response();r['message']['content']='';r['message']['tool_calls'][0]['index']=0
 msg,_=b.checked_message(r);assert 'index' not in msg['tool_calls'][0]
 r['message']['tool_calls'][0]['index']=True
 with pytest.raises(ValueError):b.checked_message(r)

def test_bounds_and_model_cannot_choose_tools():
 h=host()
 with pytest.raises(ValueError):h.dispatch({'op':'tool','name':'shell','args':{},'callId':'x'})
 h=host();h.deadline=time.monotonic()-1
 with pytest.raises(ValueError):h.dispatch({'op':'model_start'})
 h=host();h.models=4
 with pytest.raises(ValueError):h.dispatch({'op':'model_start'})

@pytest.mark.parametrize('change',[lambda rows:rows.pop(),lambda rows:rows[0].update(itemId='oil_wrong_vessel'),lambda rows:rows[0].update(label='correct'),lambda rows:rows[0].update(extra='x')])
def test_schema_only_rejects_invalid(change):
 h=host();rows=[{'itemId':i,'label':'supported','rationale':'unreviewed'} for i in h.mapping];change(rows)
 with pytest.raises(ValueError):h.predictions(json.dumps({'predictions':rows}))

def test_cli_fixture_real_pi(tmp_path):
 import subprocess
 p=subprocess.run([sys.executable,str(Path(__file__).with_name('blind_host.py')),'--fixture','--receipt',str(tmp_path/'receipt.jsonl')],capture_output=True,text=True,timeout=20)
 assert p.returncode==0 and not p.stderr
 r=json.loads(p.stdout);assert r['realPi'] and not r['realModel'] and r['nodeCompleted']
 assert r['modelCalls']==3 and r['toolCalls']==2

@pytest.mark.parametrize('which',['cases','mapping'])
def test_running_projection_binding_is_immutable(which):
 h=host();before=h.ready()['inputDigest']
 if which=='cases':h.cases[0]['claim']='changed'
 else:h.mapping['case_001']='changed'
 assert h.ready()['inputDigest']==before
 with pytest.raises(ValueError):h.dispatch({'op':'model_start'})
 assert h.closed
