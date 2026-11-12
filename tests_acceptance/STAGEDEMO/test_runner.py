"""Independent local-only runner safety checks. All paths are new synthetic test outputs."""
import hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2];SCRIPT=ROOT/'tools/stage-demo/run.sh'
def run(path,env=None,timeout=90):return subprocess.run(['bash',str(SCRIPT),'--output',str(path)],cwd=ROOT,env={**os.environ,**(env or {})},capture_output=True,text=True,timeout=timeout)
def manifest(path):return json.loads((path/'run.json').read_text())
def stopped(d):
 assert d['running'] is False
 for service in d['services'].values():
  stat=Path('/proc')/str(service['pid'])/'stat'
  if stat.exists():assert stat.read_text().rsplit(')',1)[1].split()[19]!=service['processStartTicks']

def test_optimized_runner_must_refuse_before_output(tmp_path):
 path=tmp_path/'optimized';r=run(path,{'PYTHONOPTIMIZE':'1'})
 assert r.returncode!=0,'Optimization strips mandatory assert checks but runner reported success'
 assert not path.exists(),'Unsafe optimization must be rejected before creating artifacts/services'

@pytest.mark.parametrize('kind',['directory','file','symlink','dangling'])
def test_existing_output_never_overwritten(tmp_path,kind):
 path=tmp_path/'existing';target=tmp_path/'target'
 if kind=='directory':path.mkdir();(path/'marker').write_bytes(b'keep')
 elif kind=='file':path.write_bytes(b'keep')
 elif kind=='symlink':target.write_bytes(b'keep');path.symlink_to(target)
 else:path.symlink_to(target)
 r=run(path);assert r.returncode!=0
 if kind=='directory':assert (path/'marker').read_bytes()==b'keep' and sorted(p.name for p in path.iterdir())==['marker']
 elif kind=='file':assert path.read_bytes()==b'keep'
 elif kind=='symlink':assert path.is_symlink() and target.read_bytes()==b'keep'
 else:assert path.is_symlink() and not target.exists()

def test_real_fresh_run_environment_isolation_and_verified_artifacts(tmp_path):
 path=tmp_path/'newrun';forbidden=tmp_path/'untouched';forbidden.mkdir();(forbidden/'marker').write_bytes(b'keep')
 env={'MCIS_DATA_DIR':str(forbidden),'MCIS_DB_URL':'sqlite:///'+str(forbidden/'must-not-exist.db'),'MCIS_CORE':'/nonexistent-never-execute','MCIS_PORT':'8765','MCIS_SEED_DEMO':'1','HTTP_PROXY':'http://127.0.0.1:1','HTTPS_PROXY':'http://127.0.0.1:1','ALL_PROXY':'http://127.0.0.1:1'}
 r=run(path,env);assert r.returncode==0,r.stdout+r.stderr
 d=manifest(path);assert d['status']=='passed' and d['trackReceiptReactivated'] is False;stopped(d)
 assert list(forbidden.iterdir())==[forbidden/'marker'] and (forbidden/'marker').read_bytes()==b'keep'
 assert len(d['services'])==3 and len({s['url'] for s in d['services'].values()})==3
 for service in d['services'].values():assert service['url'].startswith('http://127.0.0.1:') and not service['url'].endswith(':8765')
 for name,meta in d['artifacts'].items():
  data=(path/name).read_bytes();assert len(data)==meta['bytes'] and hashlib.sha256(data).hexdigest()==meta['sha256']
 assert json.loads((path/'source-state.json').read_text())==json.loads((path/'restored-state.json').read_text())
 checks=json.loads((path/'restored-track-receipt-check.json').read_text());assert all(x['code']=='ARCHIVE_HISTORY_ONLY' for x in checks.values())
 import sqlite3
 db=sqlite3.connect(path/'knowledge-history/mcis.db')
 for name in ('knowledge_cards','knowledge_audit','knowledge_audit_snapshots','knowledge_audit_snapshot_epoch'):assert db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0]==0
 assert db.execute('SELECT COUNT(*) FROM knowledge_archives').fetchone()[0]==1;db.close()


def test_hold_interrupt_stops_only_owned_children(tmp_path):
 path=tmp_path/'hold';p=subprocess.Popen(['bash',str(SCRIPT),'--output',str(path),'--hold'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  deadline=time.monotonic()+90
  while time.monotonic()<deadline:
   if (path/'run.json').exists():
    try:d=manifest(path)
    except json.JSONDecodeError:time.sleep(.02);continue
    if d['status']=='passed':break
   assert p.poll() is None;time.sleep(.05)
  else:raise AssertionError('runner failed to reach held passed state')
  assert d['running'] is True;p.send_signal(signal.SIGINT);assert p.wait(20)==0
  stopped(manifest(path));assert manifest(path)['status']=='passed'
 finally:
  if p.poll() is None:p.send_signal(signal.SIGINT);p.wait(20)

def test_direct_optimized_python_refuses_before_output(tmp_path):
 path=tmp_path/'direct-optimized'
 r=subprocess.run([str(ROOT/'service/.venv/bin/python'),'-O',str(ROOT/'tools/stage-demo/run.py'),'--output',str(path)],cwd=ROOT,capture_output=True,text=True,timeout=15)
 assert r.returncode!=0 and not path.exists()

def test_failure_after_three_services_cleans_owned_processes(tmp_path):
 path=tmp_path/'failed';code='''import importlib.util,sys
spec=importlib.util.spec_from_file_location("synthetic_stage",sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
original=m.Run.call
def fault(self,url,method,path,*args,**kwargs):
 if method=="POST":raise RuntimeError("Synthetic independent injected workflow failure")
 return original(self,url,method,path,*args,**kwargs)
m.Run.call=fault
sys.argv=[sys.argv[1],"--output",sys.argv[2]]
raise SystemExit(m.main())
'''
 r=subprocess.run([str(ROOT/'service/.venv/bin/python'),'-c',code,str(ROOT/'tools/stage-demo/run.py'),str(path)],cwd=ROOT,capture_output=True,text=True,timeout=60)
 assert r.returncode==1;d=manifest(path);assert d['status']=='failed' and len(d['services'])==3
 assert 'Synthetic independent' in d['error'];stopped(d)
 assert all((path/(name+'.log')).exists() for name in d['services'])

def test_browser_optimization_and_unowned_manifest_refuse(tmp_path):
 import shutil
 py=shutil.which('python');assert py
 script=ROOT/'tools/stage-demo/browser_check.py';fake=tmp_path/'fake.json'
 fake.write_text(json.dumps({'status':'passed','running':True,'services':{n:{'url':'http://127.0.0.1:8765','pid':os.getpid(),'processStartTicks':'0','dataDir':n} for n in ('source','case-restored','knowledge-history')}}))
 for optimized in (False,True):
  output=tmp_path/('bad-browser-'+str(optimized));args=[py]+(['-O'] if optimized else [])+[str(script),str(fake),'--output',str(output)]
  r=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=15)
  assert r.returncode!=0 and not output.exists()

def database_rows(path):
 import sqlite3
 result={}
 for name in ('source','case-restored','knowledge-history'):
  db=sqlite3.connect(path/name/'mcis.db');tables=db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
  result[name]={n:[tuple(row) for row in db.execute('SELECT * FROM "'+n+'"')] for n, in tables};db.close()
 return result

def test_actual_browser_same_namespace_with_audited_download(tmp_path):
 import shutil
 path=tmp_path/'browser-run';output=tmp_path/'screens'
 p=subprocess.Popen(['bash',str(SCRIPT),'--output',str(path),'--hold'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  deadline=time.monotonic()+90
  while time.monotonic()<deadline:
   if (path/'run.json').exists():
    try:d=manifest(path)
    except json.JSONDecodeError:time.sleep(.02);continue
    if d['status']=='passed':break
   assert p.poll() is None;time.sleep(.05)
  else:raise AssertionError('hold startup failed')
  before=database_rows(path)
  r=subprocess.run([shutil.which('python'),str(Path(__file__).with_name('browser_wrapper.py')),str(path/'run.json'),'--output',str(output)],cwd=ROOT,env=os.environ.copy(),capture_output=True,text=True,timeout=120)
  assert r.returncode==0,r.stdout+r.stderr
  reports=list(output.glob('*.json'));assert reports
  summaries=[json.loads(f.read_text()) for f in reports if f.name!='history-original.json']
  assert any(x.get('status')=='passed' for x in summaries)
  assert len(list(output.glob('*.png')))>=10
  assert (output/'history-original.json').read_bytes()==(path/'synthetic-knowledge.json').read_bytes()
  after=database_rows(path)
  assert after['source']==before['source'] and after['knowledge-history']==before['knowledge-history']
  old=before['case-restored'];new=after['case-restored']
  import sqlite3
  db=sqlite3.connect(path/'case-restored/mcis.db')
  for table in old:
   if table not in ('audit_events','custody_events','sqlite_sequence'):assert new[table]==old[table],table
  for table in ('audit_events','custody_events'):
   assert new[table][:len(old[table])]==old[table] and len(new[table])==len(old[table])+1,table
   columns=[r[1] for r in db.execute('PRAGMA table_info("'+table+'")')]
   line=json.loads(new[table][-1][columns.index('line')])
   assert line['operator']=='Stage Browser Readonly'
   assert line['action']=='custody.access'
   if table=='custody_events':assert new[table][-1][columns.index('kind')]=='Access'
  db.close()
  oldseq=dict(old.get('sqlite_sequence',[]));newseq=dict(new.get('sqlite_sequence',[]))
  for name in set(oldseq)|set(newseq):assert newseq.get(name)==oldseq.get(name,0)+(1 if name in ('audit_events','custody_events') else 0)

 finally:
  if p.poll() is None:p.send_signal(signal.SIGINT);p.wait(20)
  if (path/'run.json').exists():stopped(manifest(path))
