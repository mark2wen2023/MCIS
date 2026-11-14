"""Synthetic-only isolated core contract tests."""
import concurrent.futures,hashlib,json,os,pathlib,subprocess,unittest
from hfacs_source_integrity import verify_sources
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def entry(id='a',code='UA-ERR-DEC'):return dict(id=id,categoryCode=code,description='Synthetic draft',rationale='Human hypothesis')
def request():return dict(action='validate',draft=dict(scope='Synthetic work context',entries=[entry()]))
def call(data):
 p=subprocess.run([str(HERE/'mcis-hfacs.sh')],input=data if isinstance(data,str) else json.dumps(data,ensure_ascii=False),text=True,encoding='utf-8',capture_output=True,timeout=30)
 return p.returncode,json.loads(p.stdout)
def result(data):
 rc,r=call(data);assert rc==0,(rc,r);return r['result']
class Tests(unittest.TestCase):
 def test_taxonomy(self):
  r=result(dict(action='taxonomy'));cats=r['categories'];self.assertEqual(len(cats),32);self.assertEqual(len({c['code'] for c in cats}),32)
  self.assertEqual(len([c for c in cats if c['parentCode'] is None]),5)
  self.assertEqual({c['layer'] for c in cats},{'UnsafeActs','Preconditions','UnsafeSupervision','OrganizationalInfluences','ExternalFactors'})
  for c in cats:self.assertEqual(c['isLeaf'],not any(x['parentCode']==c['code'] for x in cats))
 def test_root_group_leaf(self):
  r=request();r['draft']['entries']=[entry('root','UA'),entry('group','UA-ERR'),entry('leaf')]
  es=result(r)['entries'];self.assertEqual(len(es),3)
  for e in es:self.assertEqual((e['strength'],e['reviewStatus'],e['origin']),('ToBeVerified','Draft','Investigator'));self.assertEqual(e['layer'],'UnsafeActs')
 def test_core_all_or_nothing(self):
  for invalid,code in [(entry(),'hf_duplicate_finding'),(entry('b','NOT-A-CATEGORY'),'hf_unknown_category')]:
   r=request();r['draft']['entries'].append(invalid);rc,out=call(r);self.assertEqual(rc,4);self.assertEqual(out['error']['code'],code);self.assertNotIn('result',out)
 def test_protocol(self):
  cases=['[]','{}','{"action":"taxonomy","action":"taxonomy"}','{"action":"taxonomy","extra":1}','{"action":"bad"}',' '*65537]
  for k,v in [('description',''),('description',' '),('rationale','x'*1001),('reviewStatus','Confirmed'),('strength','Strong'),('origin','Agent'),('ecfcNodeIds',[]),('id','_a'),('id','a.'),('categoryCode',1)]:
   r=request();r['draft']['entries'][0][k]=v;cases.append(r)
  for es in [[],[entry(str(i)) for i in range(33)]]:
   r=request();r['draft']['entries']=es;cases.append(r)
  for r in cases:self.assertEqual(call(r)[0],4,r)
  r=json.dumps(request()).replace('Synthetic draft','\\ud800');self.assertEqual(call(r)[0],4)
 def test_unicode_boundaries(self):
  r=request();r['draft']['entries'][0]['description']='😀'*1000;self.assertEqual(len(result(r)['entries'][0]['description']),1000)
  r['draft']['entries'][0]['description']+='😀';self.assertEqual(call(r)[0],4)
 def test_full_catalog_batch_and_idempotent(self):
  r=request();r['draft']['entries']=[entry('c'+str(i),c['code']) for i,c in enumerate(result(dict(action='taxonomy'))['categories'])]
  a=result(r);self.assertEqual(len(a['entries']),32);self.assertEqual(a,result(r))
 def test_rebuild_concurrent_source_hashes(self):
  path=HERE/'out/build-manifest.json';before=json.loads(path.read_text())
  verify_sources(ROOT,before['inputs'])
  path.unlink()
  with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rs=list(pool.map(result,[request()]*3))
  self.assertEqual(rs[0],rs[1]);self.assertEqual(rs[1],rs[2]);self.assertEqual(before,json.loads(path.read_text()))
  for f,h in before['inputs'].items():
   self.assertEqual(hashlib.sha256((ROOT/f).read_bytes()).hexdigest(),h)
  verify_sources(ROOT,json.loads(path.read_text())['inputs'])
if __name__=='__main__':unittest.main()
