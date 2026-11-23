"""Visible synthetic fixture and regression, no secrets/reports/models/services."""
import argparse,hashlib,importlib.util,json,os,subprocess,sys,unittest
from pathlib import Path
from copy import deepcopy
ROOT=Path(__file__).resolve().parent
REF='31c2a896d1717a7876a416f7d8ca295fa41378b8'
BLOBS={'timeline.py':'1c2f3457eb05833b02b1a2f79820c54c90e1118d','scoped.py':'fceca88fcbee782eca870b7c16824dd31b721d23'}
def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def dependencies(repo=None,directory=None):
 from types import ModuleType
 result=[]
 for name,blob in BLOBS.items():
  if directory:raw=(directory/name).read_bytes()
  else:
   env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0',GIT_OPTIONAL_LOCKS='0')
   raw=subprocess.check_output(['git','-C',str(repo),'--no-replace-objects','show',REF+':research/evidence-timeline-et0/'+name],env=env,timeout=10)
  assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob
  module=ModuleType(name[:-3]);sys.modules[module.__name__]=module
  exec(compile(raw,name,'exec'),module.__dict__);result.append(module)
 return result

def fixture():
 case='synthetic-clock';epoch='utc-2030-06-03T16:00:00Z-v1'
 docs={
  'panel':{'clock':'panel-local-normalized','timeState':'raw','rows':{'alarm':{'start':'70','end':'70','text':'Invented panel alarm, 2030-06-04 00:01:10 UTC+08.'}}},
  'vdr':{'clock':'vdr-aligned','timeState':'already_aligned','targetBasis':epoch,'rows':{'alarm':{'start':'-27','end':'-27','text':'Invented aligned VDR alarm, 2030-06-03 23:59:33 UTC+08.'},'sound':{'start':'-20','end':'-20','text':'Invented cabin sound at 23:59:40 UTC+08.'},'loss':{'start':None,'end':None,'text':'Invented camera does not cover cargo loss; no loss time supplied.'}}},
  'anchor':{'clock':'review-not-clock','timeState':'raw','rows':{
    'panel':{'clock':'panel-local-normalized','offset':'-97','uncertainty':'0','targetBasis':epoch},
    'vdr':{'clock':'vdr-aligned','offset':'0','uncertainty':'0','targetBasis':epoch}}}}
 originals={};pins={}
 for sid,doc in docs.items():
  doc.update(case=case,sourceId=sid,revision='v1')
  raw=json.dumps(doc,sort_keys=True,separators=(',',':')).encode();originals[sid]=raw
  pins[sid]={'case':case,'revision':'v1','sha256':hashlib.sha256(raw).hexdigest()}
 def ref(sid,key):return {'sourceId':sid,'revision':'v1','locator':'/rows/'+key}
 reviews={};selected={}
 for sid,key,start in [('panel','alarm','70'),('vdr','alarm','-27'),('vdr','sound','-20')]:
  cid=sid+'-'+key
  reviews[cid]=dict(id=cid,version='review-v1',case=case,source=ref(sid,key),clock=docs[sid]['clock'],scope={'start':start,'end':start},offset='-97' if sid=='panel' else '0',uncertainty='0',targetBasis=epoch,basis=ref('anchor',sid),status='reviewed',reviewer='synthetic-reviewer',sourceSha256=pins[sid]['sha256'],basisSha256=pins['anchor']['sha256'])
  selected[(sid,'/rows/'+key)]=cid
 return dict(case=case,originals=originals,pins=pins,reviews=reviews,selected=selected),dict(case=case,left=ref('panel','alarm'),right=ref('vdr','alarm'))

class Checks(unittest.TestCase):
 def setUp(self):self.host,self.request=fixture()
 def run_host(self,request=None):return adapter.TrialHost(**self.host,timeline=T,scoped=S).compare(self.request if request is None else request)
 def test_normal_and_unchanged(self):
  before=deepcopy((self.host,self.request));out=self.run_host()
  self.assertEqual(out['relation'],'overlap-not-identity');self.assertEqual(out['sources'][0]['displayInterval'],['-27','-27'])
  self.assertEqual(out['sources'][1]['originalSeconds'],['-27','-27']);self.assertFalse(out['authorityVerified'])
  self.assertEqual((self.host,self.request),before)
 def test_temporal_only(self):
  self.request['right']['locator']='/rows/sound';out=self.run_host();self.assertEqual(out['relation'],'before');self.assertFalse(out['causationDetermined'])
 def test_wrong_case(self):
  self.request['case']='other'
  with self.assertRaisesRegex(adapter.Rejected,'CASE'):self.run_host()
 def test_source_version_bytes_locator(self):
  for mutation in ('revision','bytes','locator'):
   self.setUp()
   if mutation=='revision':self.request['left']['revision']='v2'
   elif mutation=='bytes':self.host['originals']['panel']+=b' '
   else:self.request['left']['locator']='/rows/missing'
   with self.subTest(mutation=mutation),self.assertRaises(adapter.Rejected):self.run_host()
 def test_review_not_model_authority(self):
  for key,value in [('status','reviewed'),('offset','-97'),('reviewer','synthetic-reviewer'),('clock','vdr-aligned')]:
   bad=deepcopy(self.request);bad[key]=value
   with self.subTest(key=key),self.assertRaises(adapter.Rejected):self.run_host(bad)
 def test_unreviewed_disputed_no_review(self):
  for status in ('unreviewed','disputed'):
   self.host['reviews']['panel-alarm']['status']=status;out=self.run_host();self.assertEqual(out['relation'],'undetermined');self.assertFalse(out['sources'][0]['aligned'])
  self.host['selected'].pop(('panel','/rows/alarm'));self.assertEqual(self.run_host()['relation'],'undetermined')
 def test_repeated_panel_offset_on_aligned_vdr_rejected(self):
  # A separate synthetic host record has a matching anchor but violates aligned-row policy.
  self.host['reviews']['vdr-alarm']['offset']='-97'
  doc=json.loads(self.host['originals']['anchor']);doc['rows']['vdr']['offset']='-97'
  raw=json.dumps(doc,sort_keys=True,separators=(',',':')).encode();self.host['originals']['anchor']=raw;self.host['pins']['anchor']['sha256']=hashlib.sha256(raw).hexdigest()
  for c in self.host['reviews'].values():c['basisSha256']=self.host['pins']['anchor']['sha256']
  with self.assertRaisesRegex(adapter.Rejected,'DOUBLE_CORRECTION'):self.run_host()
 def test_double_panel_value_disagrees_with_review_basis(self):
  self.host['reviews']['panel-alarm']['offset']='-194'
  with self.assertRaisesRegex(adapter.Rejected,'BASIS_VALUES'):self.run_host()
 def test_partial_scope(self):
  doc=json.loads(self.host['originals']['panel']);doc['rows']['alarm'].update(start='69',end='70')
  raw=json.dumps(doc,sort_keys=True,separators=(',',':')).encode();self.host['originals']['panel']=raw;self.host['pins']['panel']['sha256']=hashlib.sha256(raw).hexdigest()
  self.host['reviews']['panel-alarm']['sourceSha256']=self.host['pins']['panel']['sha256']
  with self.assertRaisesRegex(ValueError,'not fully contained'):self.run_host()
 def test_no_loss_time(self):
  self.request['right']['locator']='/rows/loss';out=self.run_host();self.assertEqual(out['relation'],'undetermined');self.assertEqual(out['sources'][1]['reason'],'NO_NUMERIC_TIME')
 def test_missing_or_misbound_review(self):
  for change in ({'reviewer':''},{'version':''},{'case':'other'},{'clock':'other'}):
   self.setUp();self.host['reviews']['panel-alarm'].update(change)
   with self.subTest(change=change),self.assertRaises(adapter.Rejected):self.run_host()
 def test_distinct_basis_unresolved(self):
  # Different explicit basis remains undetermined even with reviewed records.
  c=self.host['reviews']['panel-alarm'];c['targetBasis']='other-epoch'
  doc=json.loads(self.host['originals']['anchor']);doc['rows']['panel']['targetBasis']='other-epoch'
  raw=json.dumps(doc,sort_keys=True,separators=(',',':')).encode();self.host['originals']['anchor']=raw;self.host['pins']['anchor']['sha256']=hashlib.sha256(raw).hexdigest()
  for c in self.host['reviews'].values():c['basisSha256']=self.host['pins']['anchor']['sha256']
  self.assertEqual(self.run_host()['relation'],'undetermined')
 def test_repin_does_not_rebind_old_review(self):
  self.host['originals']['panel']+=b' '
  self.host['pins']['panel']['sha256']=hashlib.sha256(self.host['originals']['panel']).hexdigest()
  with self.assertRaisesRegex(adapter.Rejected,'CALIBRATION_SOURCE_BYTES'):self.run_host()

if __name__=='__main__':
 if not sys.flags.isolated or sys.flags.optimize:raise SystemExit('Use Python -I -B without -O')
 ap=argparse.ArgumentParser();group=ap.add_mutually_exclusive_group(required=True);group.add_argument('--repo',type=Path);group.add_argument('--dependencies',type=Path);args=ap.parse_args()
 T,S=dependencies(args.repo,args.dependencies);adapter=load(ROOT/'adapter.py','trial_adapter')
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
 h,q=fixture();out=adapter.TrialHost(**h,timeline=T,scoped=S).compare(q)
 print(json.dumps({'fixedComparator':REF,'testsRun':result.testsRun,'passed':result.wasSuccessful(),'example':out,'actualHumanApprovals':0,'realAuthorizationTested':False},indent=2))
 raise SystemExit(0 if result.wasSuccessful() else 1)
