"""独立于盲测生成器的小型契约回归。"""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import ezdxf
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import s2
from s2lib import alignment, cad
from core.drawing_parser import fingerprint


class S2Contract(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_five_entrypoints(self):
        path = ROOT / "benchmarks/inputs/A/lines.dxf"
        for tool, section in s2.TOOLS.items():
            with self.subTest(tool=tool):
                dest = self.root / tool
                cmd = [
                    sys.executable,
                    str(ROOT / "scripts/s2.py"),
                    tool,
                    str(path),
                    "--out",
                    str(dest),
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                data = json.loads((dest / (tool + ".json")).read_bytes())
                if section == "validation":
                    self.assertTrue(data["valid"])
                if section == "tables":
                    self.assertEqual(len(data[0]["cells"]), 54)
                if section == "inventory":
                    self.assertEqual(data[0]["source_sha256"], fingerprint(path))

    def test_reject_tampered_si_and_blank(self):
        d = s2.process(ROOT / "benchmarks/inputs/A", self.root, None)
        c = d["tables"][0]["cells"][0]
        c.update(value_m=999, status="blank_unknown")
        v = s2.check(d)
        self.assertFalse(v["valid"])
        self.assertTrue({"unapproved_value", "incorrect_si_value"} <= set(v["issues"]))

    def test_control_matrix_and_permission(self):
        doc = ezdxf.new()
        m = doc.modelspace()
        for i, (x, y) in enumerate([(0, 0), (9, 2), (1, 8), (7, 7)]):
            m.add_text(f"CONTROL P{i} X={-y + 5} Y={x / 2} Z=1 m", dxfattribs={"insert": (x, y)})
        path = self.root / "ctrl.dxf"
        doc.saveas(path)
        d = s2.process(path, self.root, None)
        f = d["alignment"][0]["frames"][0]
        self.assertEqual(f["status"], "verified")
        f["paper_to_ship_m"][1][2] += 2
        self.assertIn("matrix_control_mismatch", s2.check(d)["issues"])
        d["validation"]["engineering_approved"] = True
        self.assertIn("unsupported_authorization", s2.check(d)["issues"])

    def test_boundary_evidence_and_duplicate_layer_names(self):
        doc = ezdxf.new()
        m = doc.modelspace()
        for x in (0, 10, 20, 30):
            m.add_line((x, 0), (x, 30))
        for y in (0, 10, 20, 30):
            m.add_line((0, y), (30, y))
        for x, y, label in [
            (2, 25, "ST"),
            (12, 25, "WL 0 m"),
            (22, 25, "WL 1 m"),
            (2, 15, "ST 0 m"),
            (2, 5, "ST 1 m"),
            (20, 15, "5"),
            (13, 5, "0"),
            (22, 5, "2"),
            (2, 36, "OFFSET TABLE (m)"),
        ]:
            m.add_text(label, dxfattribs={"insert": (x, y), "height": 1})
        f = self.root / "cross.dxf"
        doc.saveas(f)
        d = s2.process(f, self.root, None)
        cs = d["tables"][0]["cells"]
        self.assertEqual(
            sum(c["status"] == "boundary_ambiguous" and c["value"] is None for c in cs), 2
        )
        self.assertEqual(sum(c["status"] == "zero" for c in cs), 1)

    def test_raw_block_instance_transform(self):
        doc = ezdxf.new()
        b = doc.blocks.new("section-member")
        el = b.add_line((1, 2), (3, 4))
        i = doc.modelspace().add_blockref("section-member", (8, 3), dxfattribs={"rotation": 90})
        found = cad.read(doc)["curves"][0]
        self.assertEqual(found["handle"], el.dxf.handle)
        self.assertEqual(found["instance"], i.dxf.handle + "/" + el.dxf.handle)
        np.testing.assert_allclose(found["geometry"]["endpoints"][0], [1, 2, 0])
        np.testing.assert_allclose(found["samples"][0], [6, 4, 0])

    def test_bad_json_produces_validation_result(self):
        f = self.root / "bad.json"
        f.write_text('{"schema_version":2}')
        out = self.root / "check"
        p = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/s2.py"),
                "geometry_data_validate",
                str(f),
                "--out",
                str(out),
            ],
            capture_output=True,
        )
        self.assertEqual(p.returncode, 4)
        self.assertFalse(json.loads((out / "geometry_data_validate.json").read_bytes())["valid"])


if __name__ == "__main__":
    unittest.main()
