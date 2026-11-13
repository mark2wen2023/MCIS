import unittest,tempfile,sqlite3
from panel_store import Store,ROLES
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=self.tmp.name+'/panel.db';self.s=Store(self.path)
  self.snap={'caseId':'C1','reportVersion':'v1','reportText':'synthetic report','synthetic':True,'sources':{'A':{'version':'v1','text':'synthetic evidence'}}}
  self.s.create('P','investigator',self.snap)
 def tearDown(self):self.tmp.cleanup()
 def cmd(self,actor,op,payload,request=None):
  with self.s.db() as c:r=self.s._load(c,'P')['revision']
  return self.s.command('P',actor,request or 'q'+str(r),r,op,payload)
 def ready(self):
  for r in ROLES:self.cmd(r,'review',{'text':'unknown','refs':[]})
 def test_human_start(self):
  with self.assertRaises(ValueError):self.s.create('X','vessel',self.snap)
 def test_no_real_data_mode(self):
  self.snap['synthetic']=False
  with self.assertRaises(ValueError):self.s.create('X','investigator',self.snap)
 def test_copy_and_restart(self):
  self.snap['reportText']='changed';self.assertEqual('synthetic report',Store(self.path).context('P','vessel')['report']['reportText'])
 def test_initial_isolation(self):
  for r in ROLES:
   self.assertNotIn('reviews',self.s.context('P',r));self.cmd(r,'review',{'text':r,'refs':[]})
  self.assertEqual(4,len(self.s.context('P','vessel')['reviews']))
 def test_sources_not_in_packet(self):
  self.assertNotIn('text',str(self.s.context('P','vessel')['sourceManifest']))
 def test_unread_rejected_atomic(self):
  with self.assertRaises(ValueError):self.cmd('vessel','review',{'text':'x','refs':[{'sourceId':'A','version':'v1'}]})
  self.assertEqual(0,self.s.context('P','vessel')['revision'])
 def test_read_version(self):
  with self.assertRaises(ValueError):self.cmd('vessel','read_source',{'sourceId':'A','version':'v2'})
  result=self.cmd('vessel','read_source',{'sourceId':'A','version':'v1'})
  self.assertEqual('synthetic evidence',result['source']['text'])
  self.cmd('vessel','review',{'text':'x','refs':[{'sourceId':'A','version':'v1'}]})
 def test_reads_not_shared(self):
  self.cmd('vessel','read_source',{'sourceId':'A','version':'v1'})
  with self.assertRaises(ValueError):self.cmd('navigation','review',{'text':'x','refs':[{'sourceId':'A','version':'v1'}]})
 def test_idempotence(self):
  args=('P','vessel','req',0,'review',{'text':'x','refs':[]})
  a=self.s.command(*args);self.assertEqual(a,Store(self.path).command(*args));self.assertEqual(1,self.s.context('P','vessel')['revision'])
 def test_request_reuse(self):
  self.s.command('P','vessel','req',0,'review',{'text':'x','refs':[]})
  with self.assertRaises(ValueError):self.s.command('P','vessel','req',0,'review',{'text':'y','refs':[]})
 def test_stale_revision(self):
  self.cmd('vessel','review',{'text':'x','refs':[]})
  with self.assertRaises(ValueError):self.s.command('P','navigation','stale',0,'review',{'text':'y','refs':[]})
 def test_early_challenge(self):
  with self.assertRaises(ValueError):self.cmd('vessel','challenge',{'text':'x','refs':[],'target':'review:navigation'})
 def test_mutual_turns(self):
  self.ready();self.cmd('vessel','challenge',{'text':'why','refs':[],'target':'review:navigation'})
  packet=self.s.context('P','navigation');self.cmd('navigation','challenge',{'text':'response','refs':[],'target':'turn:1'})
  self.assertEqual(1,len(packet['turns']));self.assertEqual(2,len(self.s.context('P','vessel')['turns']))
 def test_self_target(self):
  self.ready()
  with self.assertRaises(ValueError):self.cmd('vessel','challenge',{'text':'x','refs':[],'target':'review:vessel'})
 def test_budget(self):
  self.ready()
  for n in range(8):self.cmd('vessel','challenge',{'text':'x','refs':[],'target':'review:navigation'})
  self.assertEqual('budget_exhausted',self.s.context('P','vessel')['phase'])
  with self.assertRaises(ValueError):self.cmd('vessel','challenge',{'text':'x','refs':[],'target':'review:navigation'})
 def test_cancel_auth_and_history(self):
  self.ready()
  with self.assertRaises(ValueError):self.cmd('vessel','cancel',{})
  self.cmd('investigator','cancel',{})
  with self.assertRaises(ValueError):self.s.context('P','vessel')
  with self.s.db() as c:self.assertEqual(4,len(self.s._load(c,'P')['reviews']))
 def test_deepcopy(self):
  self.ready();p=self.s.context('P','vessel');p['reviews']['vessel']['text']='evil'
  self.assertEqual('unknown',self.s.context('P','vessel')['reviews']['vessel']['text'])
 def test_invalid_payload(self):
  for text in ('', 'x'*4001, '\ud800'):
   with self.assertRaises((ValueError,UnicodeError)):self.cmd('vessel','review',{'text':text,'refs':[]})
 def test_unknown_command(self):
  with self.assertRaises(ValueError):self.cmd('investigator','accept_final_report',{})
 def test_two_writers_one_revision(self):
  from concurrent.futures import ThreadPoolExecutor
  def attempt(role):
   try:return Store(self.path).command('P',role,'race-'+role,0,'review',{'text':'x','refs':[]})['revision']
   except ValueError as e:return str(e)
  with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,['vessel','navigation']))
  self.assertCountEqual([1,'revision_conflict'],results)
 def test_cancel_blocks_read_receipt_replay(self):
  args=('P','vessel','read',0,'read_source',{'sourceId':'A','version':'v1'})
  self.s.command(*args);self.cmd('investigator','cancel',{})
  with self.assertRaisesRegex(ValueError,'cancelled'):Store(self.path).command(*args)
 def test_cancel_blocks_speech_receipt_replay(self):
  args=('P','vessel','review',0,'review',{'text':'sensitive fixture','refs':[]})
  self.s.command(*args);self.cmd('investigator','cancel',{})
  with self.assertRaisesRegex(ValueError,'cancelled'):self.s.command(*args)
 def test_cancel_receipt_also_denied_without_history_loss(self):
  args=('P','investigator','cancel',0,'cancel',{})
  self.s.command(*args)
  with self.assertRaisesRegex(ValueError,'cancelled'):self.s.command(*args)
  with self.s.db() as c:
   self.assertEqual(1,self.s._load(c,'P')['revision'])
   self.assertEqual(1,c.execute('SELECT count(*) FROM receipts').fetchone()[0])
 def test_invalid_source_fields_controlled_error_atomic(self):
  for field in ('sourceId','version'):
   for value in ([], {}, None, 1, '', 'x'*101):
    with self.subTest(field=field,value=value):
     payload={'sourceId':'A','version':'v1'};payload[field]=value
     with self.assertRaises(ValueError):self.cmd('vessel','read_source',payload)
     self.assertEqual(0,self.s.context('P','vessel')['revision'])
 def test_invalid_snapshot_type(self):
  for value in (None, [], 1):
   with self.assertRaises(ValueError):self.s.create('X','investigator',value)
 def test_no_host_vote(self):
  with self.assertRaises(ValueError):self.cmd('海青君','review',{'text':'x','refs':[]})
if __name__=='__main__':unittest.main()
