"""Independent synthetic HFACS core adapter acceptance; no classification truth claims."""
import json,os,subprocess,hashlib
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
def entry(i='a',code='UA-ERR-DEC'):
 return dict(id=i,categoryCode=code,description='合成任务情境 🛳',rationale='待专家核查的人工假设')
def request(entries=None):return dict(action='validate',draft=dict(scope='合成作业范围',entries=entries or [entry()]))
def call(x):
 raw=x if isinstance(x,bytes) else json.dumps(x,ensure_ascii=False).encode()
 p=subprocess.run([str(ROOT/'tools/mcis-hfacs/mcis-hfacs.sh')],input=raw,capture_output=True,timeout=40)
 return p.returncode,json.loads(p.stdout)
def good(x):
 rc,out=call(x);assert rc==0,(rc,out);return out['result']
def test_actual_catalog_every_category_and_fixed_draft():
 cats=good({'action':'taxonomy'})['categories'];assert len(cats)==32
 entries=[entry('x'+str(i),c['code']) for i,c in enumerate(cats)]
 out=good(request(entries));assert out['taxonomyVersion']=='mcis-hfacs-project/1'
 assert len(out['entries'])==32
 for c,e in zip(cats,out['entries']):
  assert c['layer']==e['layer'] and c['code']==e['categoryCode']
  assert (e['strength'],e['reviewStatus'],e['origin'])==('ToBeVerified','Draft','Investigator')
  assert c['isLeaf']==(not any(d['parentCode']==c['code'] for d in cats))
 assert sum(c['parentCode'] is None for c in cats)==5
@pytest.mark.parametrize('kind',['unknown-last','duplicate-last','status','origin','strength','ecfc','duplicate-json','invalid-utf8','unpaired-unicode'])
def test_invalid_entire_batch_has_no_partial_result(kind):
 x=request([entry('first'),entry('last')])
 if kind=='unknown-last':x['draft']['entries'][-1]['categoryCode']='NOT-REAL'
 elif kind=='duplicate-last':x['draft']['entries'][-1]['id']='first'
 elif kind in ['status','origin','strength','ecfc']:x['draft']['entries'][-1][kind]='Confirmed'
 elif kind=='duplicate-json':x=json.dumps(x).replace('"scope":','"scope":"x","scope":').encode()
 elif kind=='invalid-utf8':x=json.dumps(x).encode().replace(b'first',b'\xff')
 else:x=json.dumps(x).replace('first',r'\ud800').encode()
 rc,out=call(x);assert rc==4,out;assert out['ok'] is False and 'result' not in out
@pytest.mark.parametrize('field',['scope','description','rationale'])
def test_unicode_scalar_boundary(field):
 x=request();target=x['draft'] if field=='scope' else x['draft']['entries'][0]
 target[field]='🛳'*1000;good(x)
 target[field]+='🛳';assert call(x)[0]==4

def test_seven_source_dependencies_and_original_binary_unchanged():
 manifest=json.loads((ROOT/'tools/mcis-hfacs/out/build-manifest.json').read_text())
 sources={p:h for p,h in manifest['inputs'].items() if p.startswith('unity/')}
 assert len(sources)==7
 for p,h in sources.items():
  assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
  assert (ROOT/p).read_bytes()==(ROOT.parent/'mcis-w144'/p).read_bytes()
 assert hashlib.sha256((ROOT/'tools/mcis-core/out/mcis-core.dll').read_bytes()).hexdigest()=='f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf'
