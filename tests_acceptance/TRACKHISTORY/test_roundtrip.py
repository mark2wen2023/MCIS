"""Prepared independent contract tests; final results require explicit implementation freeze."""
import multiprocessing
import pytest
from helpers import *

@pytest.fixture
def source(tmp_path):
 with client(tmp_path/'A') as c:
  b,d,report=populate(c);yield c,b,d,report

def blocked(c,b,d):
 h=d['previewDigest'];before=state(c)
 responses=[c.get(URL+'/'+h,headers=H),c.get(URL,params={'vesselId':'ship'},headers=H),commit(c,b),c.get(URL+'/'+h+'/source',headers=H),c.get(URL+'/'+h+'/report',headers=H)]
 responses += [c.get(BASE+'/evidence/'+d[k]+'/content',headers=H) for k in ('sourceEvidenceId','reportEvidenceId')]
 for r in responses:assert r.status_code==409 and r.json()['code']=='ARCHIVE_HISTORY_ONLY',r.text;assert r.headers['cache-control']=='no-store'
 assert state(c)==before

def test_three_databases_exact_bytes_and_receipts_inactive(source,tmp_path):
 a,b,d,report=source;raw=export(a);files=unzip(raw)
 assert json.loads(files['manifest.json'])['packageVersion']=='1.3.0'
 first=json.loads(files['working-records/backup.v1.json']);assert first['version']==2
 index=[x for x in first['importHistory'] if x['kind']=='track-intake'];assert len(index)==1
 for name in ('B','C'):
  with client(tmp_path/name) as target:
   assert intake(target,raw,True).status_code==200
   blocked(target,b,d)
   assert not state(target)[0]['track_local_receipts']
   base=BASE+'/archive-history/track-imports/'+d['previewDigest']
   summary=target.get(base,headers=H);assert summary.status_code==200 and summary.json()['mode']=='archive-only' and 'replayed' not in summary.json()
   for kind,original in [('source',CSV),('report',report)]:
    r=target.get(base+'/'+kind,headers=H);assert r.status_code==200 and r.content==original and r.headers['x-sha256']==sha(original)
   raw=export(target);new=unzip(raw);current=json.loads(new['working-records/backup.v1.json'])
   assert [x for x in current['importHistory'] if x['kind']=='track-intake']==index
   for p in files:
    if p.startswith('raw/track-imports/') or p.startswith('tracks/'):assert new[p]==files[p]
   chains=[p for p in files if p.endswith('.jsonl') and ('audit' in p or 'custody' in p)]
   assert len(chains)>=2
   for p in chains:assert new[p].startswith(files[p])

@pytest.mark.parametrize('version',['1.0.0','1.1.0','1.2.0'])
@pytest.mark.parametrize('entry',['generic','preview','commit'])
def test_old_top_level_track_versions_rejected_no_mutation(source,tmp_path,version,entry):
 raw=downgrade(export(source[0]),version)
 with client(tmp_path/'reject') as c:
  before=state(c)
  r=c.post('/api/v1/cases:import',content=raw,headers={**H,'Content-Type':'application/octet-stream'}) if entry=='generic' else intake(c,raw,entry=='commit')
  assert r.status_code>=400,r.text;assert state(c)==before

def test_restored_same_vessel_new_content_rejects_new_vessel_works(source,tmp_path):
 _,b,d,_=source;raw=export(source[0])
 with client(tmp_path/'B') as c:
  assert intake(c,raw,True).status_code==200
  request=body(csv=CSV.replace(b',8,reported',b',9,reported'));preview=c.post(URL+':preview',json=request,headers=H);assert preview.status_code==200
  modified={**request,'previewDigest':preview.json()['previewDigest'],'confirmed':True}
  r=commit(c,modified);assert r.status_code==409 and r.json()['code']=='TRACK_EXISTS',r.text
  vessel(c,'newship');new=prepared(c,body(v='newship'));r=commit(c,new);assert r.status_code==200 and r.json()['replayed'] is False
  assert commit(c,new).json()['replayed'] is True
  assert len(state(c)[0]['track_local_receipts'])==1

@pytest.mark.parametrize('different',[False,True])
def test_two_actual_processes_same_sqlite_commit(tmp_path,different):
 path=tmp_path/'processes'
 with client(path) as c:
  seed(c);a=prepared(c);b=prepared(c,body(csv=CSV.replace(b',8,reported',b',9,reported'))) if different else a
 context=multiprocessing.get_context('spawn');go=context.Event();out=context.Queue();ready=[context.Event(),context.Event()]
 procs=[context.Process(target=process_commit,args=(str(path),x,ready[i],go,out)) for i,x in enumerate((a,b))]
 try:
  for p in procs:p.start()
  assert all(e.wait(20) for e in ready);go.set();results=[out.get(timeout=30),out.get(timeout=30)]
  for p in procs:p.join(15);assert p.exitcode==0
  assert sorted(r.get('status') for r in results)==([200,409] if different else [200,200]),results
  if not different:assert sorted(r['body']['replayed'] for r in results)==[False,True]
  with client(path) as c:
   assert len(state(c)[0]['track_local_receipts'])==1
   assert len(c.get(BASE+'/tracks',headers=H).json()['tracks'][0]['points'])==2
   assert c.get(BASE+'/audit:verify',headers=H).json()['valid'] is True
 finally:
  go.set()
  for p in procs:
   if p.is_alive():p.terminate()
   p.join(5)

def test_actual_new_package_rejected_by_released_reader(source,tmp_path):
 import os,sys,subprocess
 raw=export(source[0]);path=tmp_path/'actual-new.mcase';path.write_bytes(raw)
 r=subprocess.run([sys.executable,str(Path(__file__).with_name('old_reader_probe.py')),str(path),str(tmp_path/'oldtargets')],env={**os.environ,'PYTHONPATH':str(Path(os.environ['MCIS_OLD_ROOT'])/'service')},capture_output=True,text=True,timeout=30)
 assert r.returncode==0,r.stdout+r.stderr
 assert len(json.loads(r.stdout))==3

def test_real_hfacs_and_report_combination_three_databases(source,tmp_path):
 import uuid
 a,b,d,_=source
 request={'requestId':str(uuid.uuid4()),'expectedDigest':None,'draft':{'scope':'Synthetic track combination','entries':[{'id':'entry','categoryCode':'UA-ERR-DEC','description':'Synthetic hypothesis','rationale':'Not fact'}]},'expectedSources':[]}
 r=a.post(BASE+'/human-factors/hfacs:save',headers=H,json=request);assert r.status_code==200,r.text;original=r.json()['document']
 report=a.post(BASE+'/reports',headers=H,json={'templateId':'imo-cic','lang':'zh'});assert report.status_code==201,report.text;rpt=report.json()
 raw=export(a);first=unzip(raw)
 for name in ('B-combo','C-combo'):
  with client(tmp_path/name) as c:
   assert intake(c,raw,True).status_code==200
   assert c.get(BASE+'/human-factors/hfacs:draft',headers=H).json()['document']==original
   assert c.get(BASE+'/reports/'+rpt['reportId'],headers=H).json()==rpt
   r=c.post(BASE+'/human-factors/hfacs:save',headers=H,json=request);assert r.status_code==409 and r.json()['code']=='REQUEST_ARCHIVED'
   blocked(c,b,d);raw=export(c);files=unzip(raw)
   assert json.loads(files['hfacs/backup.v1.json'])==json.loads(first['hfacs/backup.v1.json'])

def test_no_w10_basic_compatibility(tmp_path):
 with client(tmp_path/'A') as c:seed(c);raw=export(c)
 assert json.loads(unzip(raw)['manifest.json'])['packageVersion']=='1.0.0'
 for entry in ('generic','restricted'):
  with client(tmp_path/entry) as c:
   r=c.post('/api/v1/cases:import',content=raw,headers={**H,'Content-Type':'application/octet-stream'}) if entry=='generic' else intake(c,raw,True)
   assert r.status_code in (200,201),r.text
