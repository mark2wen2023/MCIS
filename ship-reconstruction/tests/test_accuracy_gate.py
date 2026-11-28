import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from accuracy_gate import assess
class Gate(unittest.TestCase):
    p=dict(min_coverage=.8,max_rmse_m=.02,max_abs_m=.05,max_curve_rmse_m=.025)
    def run_case(self, values, status, policy=None):
        samples=[dict(source=k,sample=i,dy_m=v) for k,vs in values.items() for i,v in enumerate(vs)]
        self.assertEqual(assess(samples,self.p if policy is None else policy)['status'],status)
    def test_normal(self): self.run_case({'a':[.001,.002]},'passed')
    def test_offset(self): self.run_case({'a':[.03]*10},'rejected')
    def test_local(self): self.run_case({'a':[0]*99+[.06]},'rejected')
    def test_coverage(self): self.run_case({'a':[0]*10,'b':[None,0]},'insufficient_evidence')
    def test_empty(self): self.run_case({},'insufficient_evidence')
    def test_nonfinite(self): self.run_case({'a':[float('nan')]},'rejected')
    def test_curve(self): self.run_case({'a':[0]*100,'b':[.03]},'rejected')
    def test_policy(self): self.run_case({'a':[0]},'insufficient_evidence',{})
