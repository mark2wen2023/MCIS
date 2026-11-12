"""Synthetic tests only. Rebuild tests require an idle adapter."""
import json,math,os,pathlib,subprocess,tempfile,shutil,hashlib,unittest,concurrent.futures
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sample():return dict(headingDeg='0',speedKn='12',k='0.1',tSeconds='10',referenceSpeedKn='12',maxRudderDeg='35',rudderRateDegPerSec='20',commandRudderDeg='10',durationSeconds='100',provenanceNote='Synthetic test input',uncertaintyNote='Not vessel calibrated')
def call(data,cmd=None):
 p=subprocess.run(cmd or [str(HERE/'mcis-nomoto.sh')],input=data if isinstance(data,str) else json.dumps(data),text=True,capture_output=True,timeout=30)
 return p.returncode,json.loads(p.stdout)
def result(data,cmd=None):
 rc,r=call(data,cmd);assert rc==0,(rc,r);return r['result']
class Tests(unittest.TestCase):
 def test_zero(self):
  s=sample();s['commandRudderDeg']='0';r=result(s);self.assertEqual(r['baseline'],r['response'])
  p=r['baseline'][-1];self.assertAlmostEqual(p['eastM'],0);self.assertAlmostEqual(p['northM'],12*1852/3600*100,places=6);self.assertEqual(p['rudderDeg'],0)
 def test_symmetry_speed_sampling(self):
  s=sample();right=result(s);s['commandRudderDeg']='-10';left=result(s)
  self.assertEqual(len(right['response']),101)
  for i,(a,b) in enumerate(zip(right['response'],left['response'])):
   self.assertEqual(a['timeSeconds'],i);self.assertAlmostEqual(a['eastM'],-b['eastM'],places=7);self.assertAlmostEqual(a['northM'],b['northM'],places=7);self.assertEqual(a['speedKn'],12);self.assertLessEqual(abs(a['rudderDeg']),35)
 def test_steady_and_step(self):
  s=sample();s['durationSeconds']='300';r=result(s)
  self.assertAlmostEqual(r['response'][-1]['rotDegPerSec'],1,places=9)
  self.assertGreater(r['numericalDifference']['endpointDistanceM'],0)
  self.assertTrue(all(math.isfinite(v) and v>=0 for v in r['numericalDifference'].values()))
 def test_invalid(self):
  cases=['[]','{}',json.dumps(sample()).replace('"speedKn": "12"','"speedKn":"12","speedKn":"12"')]
  for key,val in [('speedKn',12),('speedKn','NaN'),('speedKn','-0.000'),('speedKn','01'),('speedKn','1e1'),('k','0'),('headingDeg','360'),('durationSeconds','10.0'),('commandRudderDeg','36'),('tSeconds','0.1'),('referenceSpeedKn','0.1'),('provenanceNote',' '),('uncertaintyNote','x'*1001),('provenanceNote','\ud800'),('x','1')]:
   s=sample();s[key]=val;cases.append(s)
  cases+=[' '*65537]
  for s in cases:self.assertEqual(call(s)[0],4,s)
 def test_bounds_unicode(self):
  s=sample();s.update(durationSeconds='1',speedKn='0',k='0.000001',tSeconds='1000',provenanceNote='😀'*1000)
  r=result(s);self.assertEqual(len(r['response']),2);self.assertEqual(r['response'][-1]['eastM'],0)
 def test_inactive_and_sources(self):
  manifest=json.loads((HERE/'out/build-manifest.json').read_text())
  for f,h in manifest['inputs'].items():
   self.assertEqual(hashlib.sha256((ROOT/f).read_bytes()).hexdigest(),h)
  with tempfile.TemporaryDirectory(prefix='nomoto-inactive-test-') as td:
   temp=pathlib.Path(td)
   for f in manifest['inputs']:
    dest=temp/f;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/f,dest)
   p=temp/'tools/mcis-nomoto/src/Program.cs';p.write_text(p.read_text().replace('double inactive=1','double inactive=7'))
   dotnet=os.environ['MCIS_DOTNET'];proj=temp/'tools/mcis-nomoto/McisNomoto.csproj';out=temp/'out'
   subprocess.run([dotnet,'build',str(proj),'-o',str(out),'-v','q'],check=True,capture_output=True,timeout=30)
   self.assertEqual(result(sample()),result(sample(),[dotnet,str(out/'mcis-nomoto.dll')]))
 def test_concurrent_rebuild(self):
  path=HERE/'out/build-manifest.json';before=json.loads(path.read_text());path.unlink();s=sample()
  with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rs=list(pool.map(result,[s]*3))
  self.assertEqual(rs[0],rs[1]);self.assertEqual(rs[1],rs[2]);self.assertEqual(before,json.loads(path.read_text()))
if __name__=='__main__':unittest.main()
