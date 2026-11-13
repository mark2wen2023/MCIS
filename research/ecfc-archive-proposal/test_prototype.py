import copy, unittest
from prototype import validate_plan

def fixture(n=2):
 h=[];r=[];before=None;prev='0'*64
 for i in range(1,n+1):
  after={'revision':i};k=str(i)
  h.append(dict(revision=i,before=before,after=after,prevHash=prev,hash=k,requestId=k,operator='synthetic',role='Lead'))
  r.append(dict(requestId=k,document=after,operator='synthetic',role='Lead'))
  before=after;prev=k
 return before,h,r

def run(v):
 # Stubs deliberately do NOT assert actual ECFC schema/hash validity.
 validate_plan(*v,lambda _:None,lambda _:None)

def test_normal():run(fixture())
def test_history_over_ui_limit():run(fixture(51))
def test_empty():run((None,[],[]))
KINDS = ['current','history_gap','float_revision','bool_revision','before','prev_hash','duplicate_request','missing_receipt','extra_receipt','receipt_document','receipt_actor','receipt_role','orphan_receipt','orphan_current']
def test_reject(kind):
 c,h,r=copy.deepcopy(fixture())
 if kind=='current':c={'revision':1}
 if kind=='history_gap':h[1]['revision']=3
 if kind=='float_revision':h[0]['revision']=1.0
 if kind=='bool_revision':h[0]['revision']=True
 if kind=='before':h[1]['before']=None
 if kind=='prev_hash':h[1]['prevHash']='wrong'
 if kind=='duplicate_request':h[1]['requestId']=h[0]['requestId']
 if kind=='missing_receipt':r.pop()
 if kind=='extra_receipt':r.append(r[0])
 if kind=='receipt_document':r[0]['document']=c
 if kind=='receipt_actor':r[0]['operator']='other'
 if kind=='receipt_role':r[0]['role']='other'
 if kind=='orphan_receipt':c=None;h=[]
 if kind=='orphan_current':h=[];r=[]
 try:run((c,h,r))
 except ValueError:return
 raise AssertionError('invalid plan accepted: '+kind)

class PlanTests(unittest.TestCase):
 def test_normal(self):test_normal()
 def test_history_over_ui_limit(self):test_history_over_ui_limit()
 def test_empty(self):test_empty()
for kind in KINDS:
 setattr(PlanTests, 'test_reject_'+kind, lambda self,k=kind:test_reject(k))
if __name__=='__main__': unittest.main(verbosity=2)
