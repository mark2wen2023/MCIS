import sys,unittest,json,copy,hashlib,importlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ecfc-archive-proposal'))
from prototype import validate_plan
from validator import decode,validate_envelope,MAX_BYTES
api=importlib.import_module('mcis_service.ecfc_drafts.router')

def fixture():
 d={'caseId':'SYNTHETIC','revision':1,'draft':{'scope':'Synthetic','nodes':[],'edges':[]},'sources':[],'validation':{'coreVersion':'mcis-ecfc-draft/1','nodes':[],'edges':[],'issues':[]},'status':'Draft','strength':'ToBeVerified','origin':'Investigator','savedBy':'Synthetic','savedRole':'LeadInvestigator','savedUtc':'2026-11-13T00:00:00Z'}
 d['digest']=hashlib.sha256(api.canonical({k:d[k] for k in ('caseId','revision','draft','sources','validation')})).hexdigest()
 e={'caseId':d['caseId'],'revision':1,'utc':d['savedUtc'],'operator':d['savedBy'],'role':d['savedRole'],'action':'ecfc.draft.save','requestId':'00000000-0000-0000-0000-000000000001','beforeDigest':None,'afterDigest':d['digest'],'before':None,'after':d,'prevHash':'0'*64}
 e['hash']=hashlib.sha256(api.canonical(e)).hexdigest()
 return {'profile':'ecfc-preflight-experiment-v0','sourceCaseId':d['caseId'],'current':d,'history':[e],'receipts':[{'requestId':e['requestId'],'document':d,'operator':e['operator'],'role':e['role']}]}
def check(d):return validate_envelope(api.canonical(d),'SYNTHETIC',api,validate_plan)
class Tests(unittest.TestCase):
 def test_valid(self):check(fixture())
 def test_tamper_hash(self):
  d=fixture();d['history'][0]['hash']='f'*64
  with self.assertRaises(api.PreviewError):check(d)
 def test_tamper_digest(self):
  d=fixture();d['current']['draft']['scope']='changed'
  with self.assertRaises(api.PreviewError):check(d)
 def test_wrong_case(self):
  d=fixture();d['sourceCaseId']='OTHER'
  with self.assertRaises(ValueError):check(d)
 def test_unknown_member(self):
  d=fixture();d['extra']=True
  with self.assertRaises(ValueError):check(d)
 def test_empty(self):
  d=fixture();d.update(current=None,history=[],receipts=[]);check(d)
 def test_size(self):
  with self.assertRaises(ValueError):decode(b' '*(MAX_BYTES+1))
 def test_duplicates(self):
  with self.assertRaises(ValueError):decode(b'{"a":{"x":1,"x":2}}')
 def test_nonfinite(self):
  for raw in (b'NaN',b'Infinity',b'1e999'):
   with self.assertRaises(ValueError):decode(raw)
 def test_unicode(self):
  for raw in (b'"\\ud800"',b'"\xff"'):
   with self.assertRaises(ValueError):decode(raw)
 def test_depth(self):
  with self.assertRaises(ValueError):decode(b'['*50+b'0'+b']'*50)
if __name__=='__main__':unittest.main(verbosity=2)
