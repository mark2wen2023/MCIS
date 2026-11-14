"""Independent offline protocol safety acceptance. No real network/model."""
import copy,json,sys,time,subprocess,hashlib
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parent))
import blind_host as b
from test_blind_host import request,tool,host

def test_full_provider_history_excludes_labels_ids_and_secret():
 c,m=b.project();calls=[];h=None
 def fake(key,messages,deadline):
  assert key=='sk-independent-dummy-secret'
  calls.append(copy.deepcopy(messages));return h.fixture_response()
 h=b.Host(c,m,fixture=False,key='sk-independent-dummy-secret',transport=fake)
 tool(h,request(h));tool(h,request(h));request(h);h.dispatch({'op':'model_end'})
 out=h.dispatch({'op':'final','payload':b.MARKER})
 raw=json.dumps(calls,ensure_ascii=False)
 for forbidden in [*m.values(),'suggestedLabel','fixture-predictions','sk-independent-dummy-secret','qualificationStatement']:
  assert forbidden not in raw
 assert out['predictions']['predictions'][0]['itemId']==m['case_001']
 assert len(calls)==3 and h.key is None

def test_project_filters_sentinel_metadata(monkeypatch):
 original,sha=b.ev.load(Path(__file__).with_name('yangze22-provisional.json'));changed=copy.deepcopy(original)
 for row in changed['items']:row['rationale']='LABEL_RATIONALE_SENTINEL';row['id']='semantic_'+row['id']
 monkeypatch.setattr(b.ev,'load',lambda _: (changed,sha))
 cases,mapping=b.project();raw=json.dumps(cases)
 assert 'LABEL_RATIONALE_SENTINEL' not in raw and 'semantic_' not in raw and 'suggestedLabel' not in raw

@pytest.mark.parametrize('damage',['id','args','extra'])
def test_canonical_tool_call_refuses_tampering(damage):
 h=host();r=request(h);h.dispatch({'op':'model_end'});call=r['message']['tool_calls'][0]
 command={'op':'tool','name':'read_blind_cases','args':{},'callId':call['id']}
 if damage=='id':command['callId']='foreign'
 elif damage=='args':command['args']={'url':'https://evil.invalid'}
 else:command['messages']=[]
 with pytest.raises(ValueError):h.dispatch(command)
 assert h.closed

def test_success_then_failed_validation_invalidates_old_candidate():
 h=host();tool(h,request(h));tool(h,request(h));assert h.validated
 bad={'id':'bad-validation','type':'function','function':{'name':'validate_predictions','arguments':json.dumps({'content':'{"predictions":[]}'})}}
 h.fixture_response=lambda:{'message':{'role':'assistant','content':None,'tool_calls':[bad]},'finish_reason':'tool_calls'}
 reply=tool(h,request(h));assert reply=={'status':'invalid','schemaOnly':True,'semanticSupportVerified':False,'errorCode':'PREDICTION_SCHEMA_OR_COVERAGE_INVALID'}
 assert h.validated is None
 h.fixture_response=lambda:{'message':{'role':'assistant','content':b.MARKER},'finish_reason':'stop'}
 request(h);h.dispatch({'op':'model_end'})
 with pytest.raises(ValueError):h.dispatch({'op':'final','payload':b.MARKER})

@pytest.mark.parametrize('damage',['cases','mapping','manifest'])
def test_post_provider_mutation_rejected(monkeypatch,damage):
 c,m=b.project();h=None
 def fake(*args):
  if damage=='cases':h.cases[0]['claim']='mutated'
  elif damage=='mapping':h.mapping['case_001']='mutated'
  else:monkeypatch.setitem(b.MANIFEST,'version','9.9.9')
  return h.fixture_response()
 h=b.Host(c,m,fixture=False,key='sk-independent-dummy-secret',transport=fake)
 with pytest.raises(ValueError):request(h)
 assert h.inflight and h.closed and h.completed==0 and h.key is None

@pytest.mark.parametrize('raw',['{"predictions":[],"predictions":[]}','{"predictions":NaN}', '['*12+'0'+']'*12])
def test_strict_bad_json(raw):
 with pytest.raises(ValueError):b.strict(raw)

@pytest.mark.parametrize('damage',['duplicate','oversize','bool','extra'])
def test_prediction_schema_bounds(damage):
 h=host();rows=[{'itemId':i,'label':'supported','rationale':'unreviewed'} for i in h.mapping]
 if damage=='duplicate':rows[-1]=rows[0]
 elif damage=='oversize':rows[0]['rationale']='x'*2001
 elif damage=='bool':rows[0]['label']=True
 else:rows[0]['expertCertified']=True
 with pytest.raises(ValueError):h.predictions(json.dumps({'predictions':rows}))

def test_deadline_buffered_line_and_tool_budget():
 line=b.Lines(0);line.pending=b'{"op":"close"}\n'
 with pytest.raises(TimeoutError):line.read(time.monotonic()-1)
 h=host();r=request(h);h.dispatch({'op':'model_end'});h.tools=8
 with pytest.raises(ValueError):h.dispatch({'op':'tool','name':'read_blind_cases','args':{},'callId':'mock-read'})

def test_cli_fixture_receipt_exclusive_private_and_no_content(tmp_path):
 receipt=tmp_path/'receipt';cmd=[sys.executable,str(Path(__file__).with_name('blind_host.py')),'--fixture','--receipt',str(receipt)]
 run=subprocess.run(cmd,capture_output=True,text=True,timeout=20);assert run.returncode==0 and not run.stderr
 out=json.loads(run.stdout);assert out['nodeCompleted'] and out['realPi'] and not out['realModel'] and out['realRequestsStarted']==0
 raw=receipt.read_text();events=[json.loads(l) for l in raw.splitlines()]
 assert receipt.stat().st_mode & 0o777==0o600
 assert events[-1]['phase']=='node_protocol_complete' and events[-2]['phase']=='cleanup_verified'
 assert sum(x['phase']=='request_attempt_started' for x in events)==3
 for forbidden in ['sourceText','claim','rationale','predictions\":','apiKey']:assert forbidden not in raw
 again=subprocess.run(cmd,capture_output=True,text=True,timeout=20);assert again.returncode==2 and receipt.read_text()==raw

def test_cli_invalid_key_fixed_error_no_echo(tmp_path):
 run=subprocess.run([sys.executable,str(Path(__file__).with_name('blind_host.py')),'--approved-blind','--receipt',str(tmp_path/'r')],input='{"apiKey":"SENTINEL_SECRET_INVALID"}\n',text=True,capture_output=True,timeout=10)
 assert run.returncode==2 and 'SENTINEL' not in run.stdout+run.stderr and not (tmp_path/'r').exists()
 assert json.loads(run.stdout)['errorCode']=='BLIND_RUN_STOPPED'
