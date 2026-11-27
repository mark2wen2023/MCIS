import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import s6


class Isolation(unittest.TestCase):
    def test_three_stage_failures_are_independent(self):
        for failed,entry in [("hull","hull_stage"),("structure","structure_stage"),("equipment","extract_equipment")]:
            with self.subTest(failed=failed),tempfile.TemporaryDirectory() as tmp:
                def fault(*args,**kwargs):
                    (args[1]/"unfinished.glb").write_bytes(b"incomplete")
                    raise RuntimeError("controlled failure at "+failed)
                out=Path(tmp)/"run"
                with patch.object(s6,entry,side_effect=fault):
                    report=s6.run(ROOT/"examples/s21/A",out)
                self.assertEqual(report,json.loads((out/"manifest.json").read_bytes()))
                self.assertEqual(report[failed]["status"],"failed")
                self.assertIn(failed,report[failed]["reason"])
                self.assertTrue((out/"diagnostics"/failed/"unfinished.glb").is_file())
                self.assertFalse((out/"unfinished.glb").exists())
                self.assertEqual(report["equipment"]["status"],"failed" if failed=="equipment" else "blocked")
                if failed!="hull":self.assertEqual(report["hull"]["status"],"exported")
                if failed!="structure":self.assertIn("observations",report["structure"])

    def test_global_input_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"out"
            report=s6.run(Path(tmp),out)
            self.assertTrue(all(report[k]["category"]=="input" for k in ("hull","structure","equipment")))
            self.assertTrue((out/"strict-quality.json").exists())

    def test_modes_are_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=ROOT/"examples/s21/A"
            for mode,notes in [("strict",["guess"]),("demo",[])]:
                with self.assertRaises(ValueError):s6.run(src,Path(tmp)/"bad",mode=mode,assumptions=notes)
            r=s6.run(src,Path(tmp)/"demo",mode="demo",assumptions=["synthetic reference origin"])
            self.assertEqual(r["hull"]["asset"]["file"],"demo-hull.glb")
            self.assertFalse(r["hull"]["formal_calculation_authorized"])
