import sys,json,copy
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parent))
import blind_host as b

def test_default_profile_identical():
 assert b.project()==b.project('yangze22-v1')
 cases,mapping=b.project();h=b.Host(cases,mapping,fixture=True)
 assert h.ready()['corpusSha256']==b.CORPUS_SHA
 assert h.ready()['inputDigest']=='b8d5ae6ea1e6afbdf72c4dbfb0ccb99de03a518dae78b1c592e91c9833db4d85'
 assert b.digest(b.MANIFEST)==b.PINNED_MANIFEST=='5a553a8dca41f1cbd1242f261d535aa66e19070c09f3b11abea5ec53c889bc9a'

@pytest.mark.parametrize('value',['../yangze22-provisional.json','/tmp/corpus.json','custom','',None,True])
def test_unknown_profile_rejected(value):
 with pytest.raises(ValueError):b.project(value)

def test_unregistered_second_profile_fails_closed(monkeypatch):
 monkeypatch.delitem(b.CASE_PROFILES,'jiangxin9-v1')
 with pytest.raises(ValueError):b.project('jiangxin9-v1')

def test_profile_change_during_run_rejected(monkeypatch):
 c,m=b.project();h=b.Host(c,m,fixture=True)
 monkeypatch.setitem(b.CASE_PROFILES,'yangze22-v1',('yangze22-provisional.json','a'*64,11))
 with pytest.raises(ValueError):h.dispatch({'op':'model_start'})
 assert h.closed

def test_profile_count_exact():
 c,m=b.project();c.pop();m.pop('case_011')
 with pytest.raises(ValueError):b.Host(c,m,fixture=True)

def test_second_profile_maximum(monkeypatch):
 monkeypatch.setitem(b.CASE_PROFILES,'jiangxin9-v1',('jiangxin9-provisional.json','a'*64,9))
 with pytest.raises(ValueError):b.case_profile('jiangxin9-v1')


def test_second_profile_registered_exact_and_blind():
 c,m=b.project('jiangxin9-v1');assert len(c)==len(m)==8
 frozen=json.loads(Path(__file__).with_name('jiangxin9-blind-input.json').read_text())
 assert frozen['cases']==c and frozen['coordinates']=='unicode_code_points'
 assert b.digest(c)=='a754aaeb1ff5a2d2852186bc513542356a3c93f44e00831ae7a686f4c6383c96'
 h=b.Host(c,m,fixture=True,case_profile_id='jiangxin9-v1')
 assert h.ready()['corpusSha256']=='f7a1a69f2f2bf51236ecfc734952c8249e87b0bbaf0e8913b006167900bff782'
 assert list(m)==[f'case_{n:03d}' for n in range(1,9)]
 for row in c:assert set(row)=={'id','sourceText','sourceSha256','sourceLocator','claim','citation'}
 rows=[{'itemId':i,'label':'insufficient','rationale':'fixture'} for i in m]
 assert len(h.predictions(json.dumps({'predictions':rows})))==8
 rows.pop()
 with pytest.raises(ValueError):h.predictions(json.dumps({'predictions':rows}))


def test_second_profile_fixture_full(tmp_path):
 import subprocess
 p=subprocess.run([sys.executable,str(Path(__file__).with_name('blind_host.py')),'--fixture','--case-profile','jiangxin9-v1','--receipt',str(tmp_path/'receipt.jsonl')],capture_output=True,text=True,timeout=20)
 assert p.returncode==0 and not p.stderr
 r=json.loads(p.stdout);assert r['realPi'] and not r['realModel'] and r['realRequestsStarted']==0
 assert len(r['predictions']['predictions'])==8
 assert r['predictions']['corpusSha256']=='f7a1a69f2f2bf51236ecfc734952c8249e87b0bbaf0e8913b006167900bff782'
 assert r['modelCalls']==3 and r['toolCalls']==2
