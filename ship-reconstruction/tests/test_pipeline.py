import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import ezdxf
from jsonschema import validate
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from geometry import transform,quality,hydro
from cad_input import declarations
from design_shell import split_levels
from reconstruct import write_asset


class PipelineTest(unittest.TestCase):
    def setUp(self):
        work=tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.work=Path(work.name)

    def call(self,path,profile=None):
        out=self.work/"run"
        cmd=[sys.executable,str(ROOT/"scripts/reconstruct.py"),str(path),"--out",str(out)]
        if profile is not None:
            config=self.work/"profile.json"
            config.write_text(json.dumps(profile))
            cmd+=["--profile",str(config)]
        proc=subprocess.run(cmd,capture_output=True,text=True,cwd=self.work)
        report=json.loads((out/"report.json").read_bytes())
        validate(report,json.loads((ROOT/"schemas/run.schema.json").read_bytes()))
        return proc,report

    def test_partition_preserves_box_volume(self):
        mesh=trimesh.creation.box()
        v,f,src=split_levels(mesh,[-.25,0.,.25])
        m=trimesh.Trimesh(v,f,process=False)
        self.assertTrue(quality(m)["closed_verified"])
        self.assertEqual(len(src),len(f))
        self.assertAlmostEqual(mesh.volume,m.volume)

    def test_analytical_submerged_box(self):
        m=trimesh.creation.box([4,2,2]);m.apply_translation([2,0,1])
        d=hydro(m,[0,.75,2])[1]
        self.assertAlmostEqual(d["volume_m3"],6)
        self.assertAlmostEqual(d["waterplane_m2"],8)
        np.testing.assert_allclose(d["center_of_buoyancy_m"],[2,0,.375],atol=1e-14)

    def test_matrix_rejects_singular_and_bool(self):
        for bad in ([0,0,0,0],[True,0,0,0]):
            mat=np.eye(4).tolist();mat[0]=bad
            with self.assertRaises(ValueError):transform(mat,[[1,2,3]])

    def test_unregistered_axes(self):
        for note in ("X forward Y port Z up", "Origin: aft. X forward Y port Z up. Y starboard"):
            self.assertFalse(declarations([{"type":"TEXT","text":note,"handle":"A"}])["frame"])

    def test_stale_witness(self):
        spec=json.loads((ROOT/"benchmarks/witness-v2/A.json").read_bytes())
        spec["source_sha256"]="0"*64
        proc,report=self.call(ROOT/"benchmarks/inputs/A",spec)
        self.assertEqual(proc.returncode,4)
        self.assertEqual(report["assets"],{})
        self.assertFalse(report["engineering_approved"])

    def test_float_export_rejects_collapsed_triangle(self):
        m=trimesh.Trimesh([[1e8,0,0],[1e8+.001,0,0],[1e8,1,0]],[[0,1,2]],process=False)
        with self.assertRaises(ValueError):write_asset(self.work,"contact","probe.glb",m,{"assets":{},"vertex_budget_m":1e-4})

    def test_parts_and_registered_concave_compartment(self):
        doc=ezdxf.readfile(ROOT/"benchmarks/inputs/A/lines.dxf")
        model=doc.modelspace()
        doc.units=6
        doc.layers.new("deck.one")
        f=model.add_3dface([(1,0,1),(3,0,1),(3,1,1),(1,1,1)],dxfattribs={"layer":"deck.one"})
        poly=model.add_lwpolyline([(0,0),(3,0),(3,1),(1,1),(1,2),(0,2)],close=True)
        note=model.add_text("HEIGHT=500 mm",dxfattribs={"insert":(400,400)})
        file=self.work/"components.dxf";doc.saveas(file)
        profile=json.loads((ROOT/"benchmarks/witness-v2/A.json").read_bytes())
        digest=hashlib.sha256(file.read_bytes()).hexdigest();profile["source_sha256"]=digest
        profile["extrusions"]=[dict(role="compartment",source="虚构底界和正向高度",source_sha256=digest,
            matrix=np.eye(4).tolist(),outline_handle=poly.dxf.handle,measure_handle=note.dxf.handle,positive_normal=[0,0,1])]
        result,r=self.call(file,profile)
        self.assertEqual(result.returncode,0,r["issues"]);self.assertEqual(r["status"],"bounded_model")
        deck,tank=r["components"]
        self.assertEqual(set(deck["handles"]),{f.dxf.handle})
        self.assertTrue(tank["enclosed_compartment_verified"])
        self.assertEqual(len(tank["handles"]),r["assets"][tank["id"]]["faces"])
        self.assertAlmostEqual(tank["quality"]["signed_volume_m3"],2.)
        self.assertEqual(tank["source"]["measure_handle"],note.dxf.handle)
        self.assertEqual(set(r["assets"]["display"]["nodes"]),{"hull",deck["id"],tank["id"]})

if __name__=="__main__":unittest.main()
