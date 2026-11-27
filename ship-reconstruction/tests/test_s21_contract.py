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

    def test_reject_unlinked_table_source(self):
        g=json.loads((ROOT/"examples/s21/A/geometry.json").read_bytes())
        g["tables"][0]["source_sha256"]="0"*64
        result=s2.check(g)
        self.assertFalse(result["valid"])
        self.assertIn("unlinked_source",result["issues"])

    def test_reject_forged_permission(self):
        g=json.loads((ROOT/"examples/s21/C/geometry.json").read_bytes())
        g["modeling_admission"]["state"]="full_research"
        self.assertFalse(s2.check(g)["valid"])

    def test_unknown_origin_remains_local(self):
        from s2lib.contract import fields
        g=json.loads((ROOT/"examples/s21/A/geometry.json").read_bytes())
        note=next(n for n in g["inventory"][0]["registration_notes"] if "ORIGIN:" in n["text"])
        note["text"]=note["text"].split("ORIGIN:")[0]+"ORIGIN: UNKNOWN"
        self.assertEqual(fields(g)["modeling_admission"]["state"],"local_symmetric")

    def test_reject_registration_without_witness(self):
        g=json.loads((ROOT/"examples/s21/A/geometry.json").read_bytes())
        curve=dict(handle="E",instance="E",source_sha256=g["inventory"][0]["source_sha256"],layout="Model",type="LINE",samples=[[0,0,0],[1,0,0]],kind="unknown",confidence="unknown",geometry={"endpoints":[[0,0,0],[1,0,0]]},ship_coordinates=[],candidates=[],ship_coordinate_candidates=[],registration_decision={"status":"cross_checked_sign","y_sign":1})
        g["curves"].append(curve)
        self.assertIn("unsupported_signed_registration",s2.check(g)["issues"])
