"""Runner lifecycle tests; actual isolated uvicorn, never business ORM fixtures."""
import importlib.util,json,os,subprocess,sys
from pathlib import Path
import pytest
P=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('stage_run',P/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_existing_output_and_dangling_symlink_refused(tmp_path):
 for output in(tmp_path/'existing',tmp_path/'link'):
  if output.name=='existing':output.mkdir();(output/'sentinel').write_text('unchanged')
  else:output.symlink_to(tmp_path/'missing')
  r=subprocess.run([sys.executable,str(P/'run.py'),'--output',str(output)],capture_output=True,timeout=10)
  assert r.returncode!=0
 assert(tmp_path/'existing/sentinel').read_text()=='unchanged'
 assert(tmp_path/'link').is_symlink()and not(tmp_path/'missing').exists()

def test_hostile_env_does_not_redirect_or_seed_actual_server(tmp_path,monkeypatch):
 sentinel=tmp_path/'untouched.db';sentinel.write_bytes(b'synthetic existing sentinel')
 monkeypatch.setenv('MCIS_DB_URL','sqlite:///'+str(sentinel));monkeypatch.setenv('MCIS_CORE','/nonexistent/hostile-script');monkeypatch.setenv('MCIS_SEED_DEMO','1');monkeypatch.setenv('HTTP_PROXY','http://127.0.0.1:1');monkeypatch.setenv('HTTPS_PROXY','http://127.0.0.1:1')
 output=tmp_path/'run';output.mkdir();run=m.Run(output)
 try:
  url=run.start('source');assert run.j(url,'GET','/api/v1/cases')==[]
  item=json.loads((output/'run.json').read_text())['services']['source']
  assert item['processStartTicks']==m.process_start_ticks(item['pid'])
  assert isinstance(item['processStartTicks'],str)and item['processStartTicks'].isdigit()
  assert(output/'source/mcis.db').exists();assert sentinel.read_bytes()==b'synthetic existing sentinel'
 finally:run.stop()
 assert all(p.poll()is not None for p,_ in run.children)
 assert json.loads((output/'run.json').read_text())['running']is False

def test_failure_stops_only_owned_process_and_retains_artifacts(tmp_path,monkeypatch):
 output=tmp_path/'failed';monkeypatch.setattr(sys,'argv',['run.py','--output',str(output)])
 def fail(run):run.start('source');raise RuntimeError('synthetic step failure')
 monkeypatch.setattr(m.Run,'execute',fail)
 assert m.main()==1
 manifest=json.loads((output/'run.json').read_text());assert manifest['status']=='failed'and manifest['running']is False
 assert(output/'source/mcis.db').exists()and(output/'source.log').exists()


def test_proc_identity_failure_cleans_only_owned_child(tmp_path,monkeypatch):
 output=tmp_path/'identity-failure';output.mkdir();run=m.Run(output)
 def fail(pid):raise RuntimeError('synthetic process identity unavailable')
 monkeypatch.setattr(m,'process_start_ticks',fail)
 try:
  with pytest.raises(RuntimeError,match='identity unavailable'):run.start('source')
 finally:run.stop()
 assert len(run.children)==1
 assert run.children[0][0].poll()is not None
 assert json.loads((output/'run.json').read_text())['running']is False
 assert(output/'source.log').exists()
