import hashlib
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import s6


class Delivery(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.src = self.base / "in"
        self.src.mkdir()
        self.drawing = self.src / "drawing.dxf"
        shutil.copyfile(ROOT / "examples/s21/A/input.dxf", self.drawing)
        self.out = self.base / "original"

    def inventory(self, report, folder):
        index = {row["path"]: row for row in report["files"]}
        actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
        self.assertEqual(actual - {"manifest.json"}, set(index))
        for name, row in index.items():
            data = (folder / name).read_bytes()
            self.assertEqual((len(data), hashlib.sha256(data).hexdigest()), (row["bytes"], row["sha256"]))
            self.assertEqual(row["mode"], report["mode"])
        self.assertEqual(s6.verify(folder), report)
        return index

    def test_recursive_roles_tamper_extra_and_missing(self):
        r = s6.run(self.src, self.out)
        index = self.inventory(r, self.out)
        for path, role in [("strict-hull.glb", "strict_delivery"), ("geometry.json", "intermediate_evidence"),
                           ("structure/evidence-graph.json", "intermediate_evidence"), ("structures.log", "diagnostic")]:
            self.assertEqual(index[path]["role"], role)
        nested = self.out / "structure/structures.json"
        data = nested.read_bytes()
        nested.write_bytes(data + b" ")
        with self.assertRaises(ValueError): s6.verify(self.out)
        nested.unlink()
        with self.assertRaises(ValueError): s6.verify(self.out)
        nested.write_bytes(data)
        (self.out / "extra").touch()
        with self.assertRaises(ValueError): s6.verify(self.out)

    def test_detected_input_change_restored_later_still_revokes(self):
        old = self.drawing.read_bytes()
        hull, structure = s6.hull_stage, s6.structure_stage
        def mutate(*args):
            r = hull(*args)
            self.drawing.write_bytes(old + b"\n")
            return r
        def restore(*args):
            self.drawing.write_bytes(old)
            return structure(*args)
        with patch.object(s6, "hull_stage", mutate), patch.object(s6, "structure_stage", restore):
            r = s6.run(self.src, self.out)
        self.assertTrue(all(r[s]["category"] == "input" for s in s6.STAGES))
        index = self.inventory(r, self.out)
        self.assertFalse(any(v["role"] in ("strict_delivery", "research_demo") for v in index.values()))

    def test_partial_write_failure_and_recovery(self):
        def partial(path, *args, **kwargs):
            path.write_bytes(b"partial mesh")
            raise OSError("injected disk write failure")
        with patch.object(s6, "export_mesh", partial):
            r = s6.run(self.src, self.out)
        original = (self.out / "manifest.json").read_bytes()
        index = self.inventory(r, self.out)
        self.assertEqual(r["hull"]["status"], "failed")
        self.assertEqual(index["diagnostics/hull/strict-hull.glb"]["role"], "diagnostic")
        recovered = self.base / "recovered"
        r = s6.run(self.src, recovered, recover_from=self.out)
        self.assertEqual(r["hull"]["status"], "exported")
        self.assertEqual(r["recovery"]["previous_manifest_sha256"], hashlib.sha256(original).hexdigest())
        self.inventory(r, recovered)
        self.assertEqual(original, (self.out / "manifest.json").read_bytes())
        with self.assertRaises(ValueError):
            s6.run(self.src, self.base / "mixed", recover_from=self.out, mode="demo", assumptions=["example"])
        self.drawing.write_bytes(self.drawing.read_bytes() + b" ")
        with self.assertRaises(ValueError): s6.run(self.src, self.base / "changed", recover_from=self.out)

    def test_interrupted_seal_and_recovery(self):
        save = s6.save
        def interrupt(path, value):
            if value.get("sealed") is True:
                raise OSError("injected manifest write failure")
            save(path, value)
        with patch.object(s6, "save", interrupt), self.assertRaises(OSError):
            s6.run(self.src, self.out)
        with self.assertRaises(ValueError): s6.verify(self.out)
        recovered = self.base / "retry"
        self.inventory(s6.run(self.src, recovered, recover_from=self.out), recovered)

    def test_demo_roles(self):
        r = s6.run(self.src, self.out, mode="demo", assumptions=["synthetic datum"])
        index = self.inventory(r, self.out)
        self.assertEqual(index["demo-hull.glb"]["role"], "research_demo")
        self.assertNotIn("strict_delivery", {row["role"] for row in index.values()})

    def test_publication_failure_after_first_file(self):
        real_rename = Path.rename
        moved = []
        def inject(path, target):
            if path.parent.name == ".running-hull" and Path(target).parent == self.out:
                if moved:
                    raise OSError("injected publication failure")
                moved.append(path.name)
            return real_rename(path, target)
        with patch.object(Path, "rename", inject):
            r = s6.run(self.src, self.out)
        self.assertEqual(len(moved), 1)
        self.assertEqual(r["hull"]["status"], "failed")
        rows = self.inventory(r, self.out)
        self.assertTrue(all(rows["diagnostics/hull/" + name]["role"] == "diagnostic"
                            for name in ("geometry.json", "strict-hull.glb")))
        self.assertNotIn("strict-hull.glb", rows)

    def test_nested_input_same_sources_for_all_stages(self):
        folder = self.src / "revision"
        folder.mkdir()
        self.drawing.rename(folder / "drawing.dxf")
        r = s6.run(self.src, self.out)
        self.assertEqual(set(r["request"]["drawings"]), {"revision/drawing.dxf"})
        self.assertEqual(r["hull"]["status"], "exported")
        self.assertEqual(r["structure"]["status"], "blocked")
        self.assertIn("observations", r["structure"])
        self.inventory(r, self.out)
