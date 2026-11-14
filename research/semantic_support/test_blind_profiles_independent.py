"""Independent second fixed-profile safety regression; never calls a real API."""
import sys,json,copy,subprocess,hashlib
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parent))
import blind_host as b
from test_blind_host import request,tool
ROOT=Path(__file__).parent
SHA='f7a1a69f2f2bf51236ecfc734952c8249e87b0bbaf0e8913b006167900bff782'
INPUT='a754aaeb1ff5a2d2852186bc513542356a3c93f44e00831ae7a686f4c6383c96'

def test_second_projection_frozen_and_no_answer_fields():
 cases,mapping=b.project('jiangxin9-v1');frozen=json.loads((ROOT/'jiangxin9-blind-input.json').read_text())
 assert len(cases)==len(mapping)==8 and b.digest(cases)==INPUT and frozen['cases']==cases
 assert hashlib.sha256((ROOT/'jiangxin9-provisional.json').read_bytes()).hexdigest()==SHA
 raw=json.dumps(cases)
 assert all(i not in raw for i in mapping.values())
 assert not any(x in raw for x in ('suggestedLabel','rationale','expert','fixture-predictions'))
 assert [x['id'] for x in cases]==[f'case_{i:03}' for i in range(1,9)]

@pytest.mark.parametrize('value',['../../x','/tmp/a','https://evil.invalid/a','jiangxin9-provisional.json',{},False])
def test_unknown_profile_never_loads_file(monkeypatch,value):
 monkeypatch.setattr(b.ev,'load',lambda _: (_ for _ in ()).throw(AssertionError('must not read')))
 with pytest.raises(ValueError):b.project(value)

@pytest.mark.parametrize('damage',['filename','sha','count'])
def test_corrupt_fixed_profile_rejected(monkeypatch,damage):
 filename,sha,count=b.CASE_PROFILES['jiangxin9-v1']
 if damage=='filename':filename='/tmp/jiangxin9-provisional.json'
 elif damage=='sha':sha='a'*64
 else:count=7
 monkeypatch.setitem(b.CASE_PROFILES,'jiangxin9-v1',(filename,sha,count))
 with pytest.raises(ValueError):b.project('jiangxin9-v1')

def test_second_canonical_history_no_original_ids_or_labels():
 c,m=b.project('jiangxin9-v1');calls=[];h=None
 def fake(key,msgs,deadline):calls.append(copy.deepcopy(msgs));return h.fixture_response()
 h=b.Host(c,m,fixture=False,key='sk-independent-dummy-secret',transport=fake,case_profile_id='jiangxin9-v1')
 tool(h,request(h));tool(h,request(h));request(h);h.dispatch({'op':'model_end'});r=h.dispatch({'op':'final','payload':b.MARKER})
 assert r['predictions']['corpusSha256']==SHA and r['inputDigest']==INPUT and len(r['predictions']['predictions'])==8
 assert [x['itemId'] for x in r['predictions']['predictions']]==list(m.values())
 raw=json.dumps(calls);assert all(x not in raw for x in m.values());assert 'suggestedLabel' not in raw and 'sk-independent' not in raw

@pytest.mark.parametrize('which',['profile','mapping','input'])
def test_second_post_request_mutation_rejected(monkeypatch,which):
 c,m=b.project('jiangxin9-v1');h=None
 def fake(*args):
  if which=='profile':monkeypatch.setitem(b.CASE_PROFILES,'jiangxin9-v1',('jiangxin9-provisional.json','a'*64,8))
  elif which=='mapping':h.mapping['case_001']='changed'
  else:h.cases[0]['claim']='changed'
  return h.fixture_response()
 h=b.Host(c,m,fixture=False,key='sk-independent-dummy-secret',transport=fake,case_profile_id='jiangxin9-v1')
 with pytest.raises(ValueError):request(h)
 assert h.closed and h.inflight and h.key is None

def test_cross_profile_count_refused():
 c,m=b.project('jiangxin9-v1')
 with pytest.raises(ValueError):b.Host(c,m,fixture=True)
 h=b.Host(c,m,fixture=True,case_profile_id='jiangxin9-v1')
 rows=[{'itemId':i,'label':'supported','rationale':'fixture'} for i in m]
 for bad in [rows[:-1],rows+[rows[0]],rows[:-1]+[dict(rows[-1],itemId='case_009')]]:
  with pytest.raises(ValueError):h.predictions(json.dumps({'predictions':bad}))

def test_actual_pi_second_fixture_and_receipt(tmp_path):
 path=tmp_path/'receipt'
 proc=subprocess.run([sys.executable,str(ROOT/'blind_host.py'),'--fixture','--case-profile','jiangxin9-v1','--receipt',str(path)],text=True,capture_output=True,timeout=20)
 assert proc.returncode==0 and not proc.stderr
 r=json.loads(proc.stdout);assert r['nodeCompleted'] and r['realPi'] and not r['realModel'] and r['realRequestsStarted']==0
 assert r['modelCalls']==3 and r['toolCalls']==2 and len(r['predictions']['predictions'])==8
 events=[json.loads(x) for x in path.read_text().splitlines()];assert events[1]['corpusSha256']==SHA and events[1]['inputDigest']==INPUT
 assert events[-1]['phase']=='node_protocol_complete'
