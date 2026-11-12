"""Synthetic-only protocol/core integration tests. Cold-build test: run when CLI idle."""
import concurrent.futures, hashlib, json, os, pathlib, subprocess, unittest
HERE=pathlib.Path(__file__).resolve().parent
def node(id,kind='Threat',barrierId=None):return dict(id=id,label=id,kind=kind,barrierId=barrierId)
def edge(a,b):return dict(fromId=a,toId=b)
def model():return dict(hazard='Synthetic hazard',topEvent=dict(id='top',label='Synthetic loss'),nodes=[node('t'),node('c','Consequence')],edges=[edge('t','top'),edge('top','c')])
def run(m):
 p=subprocess.run([str(HERE/'mcis-bowtie.sh')],input=m if isinstance(m,str) else json.dumps(m),text=True,capture_output=True,timeout=45)
 return p.returncode,json.loads(p.stdout)
def result(m):rc,r=run(m);assert rc==0,(rc,r);return r['result']
class Tests(unittest.TestCase):
 def test_direct_no_barriers(self):
  r=result(model());self.assertTrue(r['structureValid']);self.assertEqual((r['nodeCount'],r['edgeCount']),(3,2));self.assertEqual(r['notCheckedRefCount'],0)
 def test_empty_and_orphans(self):
  m=model();m['nodes']=[];m['edges']=[];r=result(m);self.assertFalse(r['structureValid']);self.assertEqual(r['validationIssues'][0]['code'],'sys_empty_model')
  m=model();m['nodes']+=[node('b','PreventionBarrier')];m['edges']=[];r=result(m);self.assertEqual({i['code'] for i in r['validationIssues']},{'sys_orphan_threat','sys_orphan_consequence','sys_orphan_barrier'})
 def test_deferred_escalation(self):
  m=model();m['nodes']=[node('e','EscalationFactor','b')]+m['nodes']+[node('b','PreventionBarrier')];m['edges']=[edge('t','b'),edge('b','top'),edge('top','c')];self.assertTrue(result(m)['structureValid'])
 def test_construction_errors(self):
  for es,code in [([edge('top','t')],'sys_invalid_edge'),([edge('missing','top')],'sys_unknown_node'),([edge('t','top')]*2,'sys_duplicate_edge')]:
   m=model();m['edges']=es;r=result(m);self.assertEqual(r['constructionErrors'][0]['code'],code);self.assertFalse(r['structureValid']);self.assertEqual(r['validationIssues'],[])
  m=model();m['nodes']+=[node('t')];r=result(m);self.assertEqual(r['nodeCount'],3);self.assertEqual(r['edgeCount'],0);self.assertEqual(r['constructionErrors'][0]['code'],'sys_duplicate_id')
  m=model();m['nodes']+=[node('t2')];m['edges']=[edge('t','t2'),edge('t2','t')];self.assertEqual(result(m)['constructionErrors'][0]['code'],'sys_cycle')
  m=model();m['nodes']+=[node('e','EscalationFactor','c')];self.assertEqual(result(m)['constructionErrors'][0]['code'],'sys_invalid_edge')
 def test_invalid_protocol(self):
  cases=['{}','[]','{"hazard":"a","hazard":"b"}','{"hazard":NaN}']
  for key,value in [('hazard',' '),('hazard','x'*501),('nodes',[node('t')]*65),('edges',[edge('t','top')]*129),('state','Effective')]:
   m=model();m[key]=value;cases.append(m)
  for changed in [dict(id='t.x'),dict(strength='Strong'),dict(kind='TopEvent'),dict(barrierId='b'),dict(id='x\n')]:
   m=model();m['nodes'][0].update(changed);cases.append(m)
  cases+=[' '*131073,json.dumps(model()).replace('"id": "t"','"id": "t", "id": "x"')]
  for m in cases:
   rc,r=run(m);self.assertEqual(rc,4,m);self.assertFalse(r['ok'])
 def test_unicode_and_invalid_top_id(self):
  for length in [250,500]:
   m=model();m['hazard']='😀'*length;m['topEvent']['label']='😀'*length;self.assertTrue(result(m)['structureValid'])
  m=model();m['hazard']='😀'*501;self.assertEqual(run(m)[0],4)
  m=model();m['hazard']='\ud800';self.assertEqual(run(m)[0],4)
  m=model();m['topEvent']['id']='_top';r=result(m);self.assertEqual(r['nodeCount'],0);self.assertFalse(r['structureValid']);self.assertEqual(r['constructionErrors'][0]['code'],'sys_invalid_id')
 def test_bounds(self):
  m=model();m['hazard']='x'*500;m['nodes']=[node('x'*64)]+[node('n'+str(i)) for i in range(63)];m['edges']=[];self.assertEqual(result(m)['nodeCount'],65)
 def test_determinism_sources_rebuild_and_concurrency(self):
  receipt=HERE/'out/build-manifest.json';before=json.loads(receipt.read_text());r=result(model());self.assertEqual(r,result(model()))
  receipt.unlink()
  with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
   self.assertEqual(list(pool.map(result,[model()]*3)),[r]*3)
  after=json.loads(receipt.read_text());self.assertEqual(before,after)
  root=HERE.parents[1]
  for f,h in after['inputs'].items():self.assertEqual(hashlib.sha256((root/f).read_bytes()).hexdigest(),h)
if __name__=='__main__':unittest.main()
