"""Synthetic standalone adapter tests, no incident or personnel data."""
import concurrent.futures,datetime as dt,hashlib,json,os,pathlib,shutil,subprocess,unittest
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
START=dt.datetime(2026,1,1,tzinfo=dt.timezone.utc)
def stamp(h):return (START+dt.timedelta(hours=h)).strftime('%Y-%m-%dT%H:%M:%SZ')
def row(a,b,kind='Rest'):return dict(startUtc=stamp(a),endUtc=stamp(b),kind=kind)
def req(end=24,rows=None):return dict(recordStartUtc=stamp(0),recordEndUtc=stamp(end),intervals=rows or [row(0,10),row(10,end,'Watch')])
def run(data):
 raw=data if isinstance(data,str) else json.dumps(data)
 p=subprocess.run([str(HERE/'mcis-rest.sh')],input=raw,text=True,capture_output=True,timeout=40)
 return p.returncode,json.loads(p.stdout),p.stderr
class Tests(unittest.TestCase):
 def good(self,d):
  rc,o,err=run(d);self.assertEqual(rc,0,err+str(o));self.assertTrue(o['ok']);return o['result']
 def bad(self,d):
  rc,o,_=run(d);self.assertEqual(rc,4);self.assertFalse(o['ok'])
 def test_10h_exact_and_second_below(self):
  a=self.good(req());self.assertFalse(any(f['rule']=='Rest24h' for f in a['findings']))
  b=self.good(req(rows=[row(0,10-1/3600),row(10-1/3600,24,'Watch')]))
  self.assertTrue(any(f['rule']=='Rest24h' for f in b['findings']))
 def test_week_77h_and_below(self):
  rows=[]
  for day in range(7):rows.extend([row(day*24,day*24+11),row(day*24+11,(day+1)*24,'Watch')])
  a=self.good(req(168,rows));self.assertEqual(a['totals']['restHours'],77);self.assertFalse(any(f['rule']=='Rest7d' for f in a['findings']))
  rows[-2]['endUtc']=stamp(155-1/3600);rows[-1]['startUtc']=stamp(155-1/3600)
  b=self.good(req(168,rows));self.assertTrue(any(f['rule']=='Rest7d' for f in b['findings']))
 def test_unknown_preserved(self):
  a=self.good(req(24,[row(0,5)]));self.assertEqual(a['totals'],dict(restHours=5,workHours=0,unknownHours=19));self.assertTrue(a['insufficientData'])
 def test_short_windows_not_claimed(self):
  a=self.good(req(5,[row(0,5)]));self.assertFalse(a['coverage']['has24hWindow']);self.assertFalse(a['coverage']['has7dWindow']);self.assertNotIn('isCompliant',a);self.assertNotIn('isConclusive',a)
 def test_no_work_rule(self):
  rows=[]
  for day in range(7):rows.extend([row(day*24,day*24+11),row(day*24+11,(day+1)*24,'OtherWork')])
  a=self.good(req(168,rows));self.assertEqual(a['totals']['workHours'],91);self.assertFalse(any(f['rule'].startswith('Work') for f in a['findings']))
 def test_all_invalid(self):
  cases=[]
  for name,val in [('thresholds',{}),('ApplyWorkHourLimits',True),('exceptions',True)]:
   x=req();x[name]=val;cases.append(x)
  for val in ['2026-01-01T00:00:00+00:00','2026-01-01T00:00:00.0Z','1899-01-01T00:00:00Z','2101-01-01T00:00:00Z','2026-02-30T00:00:00Z',None]:
   x=req();x['recordStartUtc']=val;cases.append(x)
  for intervals in [[],[row(0,11),row(10,24,'Watch')],[row(-1,10)],[row(0,0)],[row(0,1,'Work')],[row(0,1)]*257]:
   x=req();x['intervals']=intervals;cases.append(x)
  cases.append(req(337,[row(0,337)]));cases.append(req(0,[row(0,1)]))
  cases.extend(['{"recordStartUtc":"x","recordStartUtc":"y"}','NaN','[]',json.dumps(req()).replace('"kind": "Rest"','"kind":"Rest","kind":"Watch"'),' '*131073])
  for case in cases:
   with self.subTest(case=str(case)[:100]):self.bad(case)
 def test_deterministic_and_source_unchanged(self):
  paths=[ROOT/'unity/Assets/_Project/Scripts/Domain/HumanFactors/RestHours.cs',ROOT/'tools/mcis-core/out/mcis-core.dll']
  before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.exists()}
  a=self.good(req());b=self.good(req());self.assertEqual(a,b)
  self.assertEqual(before,{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.exists()})
  manifest=json.loads((HERE/'out/build-manifest.json').read_text())
  self.assertEqual(manifest['inputs']['unity/Assets/_Project/Scripts/Domain/HumanFactors/RestHours.cs'],before[str(paths[0])])
  for name,h in manifest['artifacts'].items():self.assertEqual(hashlib.sha256((HERE/'out'/name).read_bytes()).hexdigest(),h)
 def test_reproducible_rebuild(self):
  self.good(req());before=hashlib.sha256((HERE/"out/mcis-rest.dll").read_bytes()).hexdigest()
  (HERE/"out/build-manifest.json").unlink()
  self.good(req());self.assertEqual(before,hashlib.sha256((HERE/"out/mcis-rest.dll").read_bytes()).hexdigest())
 def test_concurrent_cold_build(self):
  shutil.rmtree(HERE/'out',ignore_errors=True)
  with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:out=list(pool.map(lambda _:run(req()),range(3)))
  self.assertTrue(all(r[0]==0 for r in out),out);self.assertTrue(all(r[1]==out[0][1] for r in out))
if __name__=='__main__':unittest.main(verbosity=2)
