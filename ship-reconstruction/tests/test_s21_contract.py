import copy
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import s2


class Contract(unittest.TestCase):
    def test_examples_from_source(self):
        for name,state in zip("ABC",["full_research","local_symmetric","blocked"]):
            with self.subTest(name=name):
                path=ROOT/"examples/s21"/name
                g=s2.process(path/"input.dxf",path,None)
                self.assertEqual(json.loads(json.dumps(g)),json.loads((path/"geometry.json").read_bytes()))
                self.assertTrue(g["validation"]["valid"])
                self.assertEqual(g["modeling_admission"]["state"],state)
                self.assertFalse(g["modeling_admission"]["engineering_approved"])
                if name=="B": self.assertEqual(g["uncertainties"][-1]["candidate_y_multipliers"],[1,-1])
                if name=="C": self.assertEqual(set(g["conflicts"][0]["raw_values"]),{"1.5","1.9"})

    def test_reject_forged_permission(self):
        g=json.loads((ROOT/"examples/s21/C/geometry.json").read_bytes())
        g["modeling_admission"]["state"]="full_research"
        self.assertFalse(s2.check(g)["valid"])
