import json
import sys
import tempfile
import unittest
from pathlib import Path
import ezdxf
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from geometry import read_exchange,exchange
from coordinate_contract import contract,convert,joint_in_exchange,export_mesh,read_meta
from s6_equipment.runtime import Runtime
from s6_equipment.standard_export import convert as standard
from s6 import run

class Integration(unittest.TestCase):
    def test_large_origin_and_repeat(self):
        origin=[2.**24,-2.**23,4.]
        m=contract("vessel",origin)
        p=np.array([origin])+[.001,2.,3.]
        q=convert(p,"vessel","gltf_y_up",m)
        np.testing.assert_allclose(convert(q,"gltf_y_up","vessel",m),p,atol=1e-10,rtol=0)
        with self.assertRaises(ValueError):convert(q,"gltf_y_up","gltf_y_up",m)
        with self.assertRaises(ValueError):contract("vessel",[True,2,3])
        j=joint_in_exchange(origin,[0.,0.,1.],"vessel",m)
        self.assertEqual(j["axis"],[0.,1.,0.]);self.assertEqual(j["pivot_m"],[0.,0.,0.])
        with tempfile.TemporaryDirectory() as tmp:
            mesh=trimesh.creation.box(extents=[.001,2.,3.]);mesh.apply_translation(origin)
            asset=export_mesh(Path(tmp)/"mesh.glb",mesh,m);self.assertLess(asset["vertex_max_error_m"],1e-7)
            np.testing.assert_allclose(read_exchange(Path(tmp)/"mesh.glb").vertices,mesh.vertices,rtol=0,atol=1e-7)
            with self.assertRaises(ValueError):exchange(exchange(mesh))

    def test_shared_synthetic_drawing(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);src=base/"in";src.mkdir();out=base/"results"
            doc=ezdxf.readfile(ROOT/"examples/s21/A/input.dxf");m=doc.modelspace()
            for i,s in enumerate(["FRAME X FORWARD Y PORT Z UP; METRES; INSERT IS PIVOT",
                                 "EQUIPMENT antenna Radar length=2 width=.3 height=.15",
                                 "EQUIPMENT blade Rudder chord=.7 span=1.2 thickness=.1 axis_fraction=.15"]):
                m.add_text(s,dxfattribs={"insert":(1,2,i+3),"height":.1})
            doc.saveas(src/"test.dxf")
            r=run(src,out,synthetic=True)
            self.assertEqual(r["hull"]["status"],"exported")
            a=r["equipment"]["assets"][0];cfg=json.loads((out/a["json"]).read_bytes())
            self.assertEqual(read_meta(out/a["file"])["coordinates"],cfg["coordinates"])
            scene=trimesh.load_scene(out/a["file"],process=False)
            rt=Runtime(scene,cfg);fixed,geo=scene.graph["structure_hull"]
            h=scene.geometry[geo].copy();h.apply_transform(fixed)
            np.testing.assert_allclose(h.bounds,[[0,0,-1.5],[6,2,1.5]],atol=1e-6)
            rt.step("antenna",15,.1)
            np.testing.assert_array_equal(scene.graph["structure_hull"][0],fixed)
            with self.assertRaises(ValueError):rt.step("blade",3,1)
            with self.assertRaises(ValueError):standard(scene,cfg)
