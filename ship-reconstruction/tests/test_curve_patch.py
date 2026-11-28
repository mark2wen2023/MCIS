import sys
from pathlib import Path
import unittest
import ezdxf
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from curve_patch import surfaces
from geometry import read_curves


class RegisteredCurves(unittest.TestCase):
    def test_fitted_polyline_excludes_control_polygon(self):
        doc=ezdxf.new()
        line=doc.modelspace().add_polyline2d([(0,0),(1,20),(0,1),(1,2)])
        line.dxf.flags |= 4
        for v,flag in zip(line.vertices,[16,16,8,8]):v.dxf.flags=flag
        result,=read_curves(doc,[dict(handle=line.dxf.handle,source="drawing",kind="waterline",
                         use="constraint",matrix=np.eye(4).tolist())])
        self.assertEqual(result["points_m"],[[0.,1.,0.],[1.,2.,0.]])

    def test_open_regions_and_source_isolation(self):
        doc=ezdxf.new();sha="0"*64
        curves=[]
        for z in [1.,2.]:
            e=doc.modelspace().add_line((0,1,z),(2,2,z))
            curves.append(dict(source_sha256=sha,handle=e.dxf.handle,source="label and datum",matrix=np.eye(4).tolist(),
                               use="constraint",kind="waterline"))
        r=dict(id="ok",curves=curves,stations_m=[0.,1.,2.],frame_evidence="registered design views")
        bad=dict(r,id="wrong",curves=[{**c,"source_sha256":"x"} for c in curves])
        a,b=surfaces([dict(sha256=sha,cad=doc)],[bad,r])
        self.assertIsNone(a[1])
        self.assertIsNone(b[2])
        mesh,faces,detail,_=b[1]
        self.assertEqual(len(faces),4)
        self.assertFalse(mesh.is_watertight)
        self.assertTrue(all(len(f["handles"])==2 for f in faces))

    def test_partial_delivery_through_s6(self):
        import json
        import tempfile
        from s6 import run, verify
        from cad_input import fingerprint
        from coordinate_contract import read_meta
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);src=base/"source";src.mkdir()
            drawing=src/"input.dxf";doc=ezdxf.new()
            specs=[]
            for z in (0.,1.):
                e=doc.modelspace().add_line((0.,1.,z),(3.,2.,z))
                specs.append(dict(handle=e.dxf.handle,kind="waterline",use="constraint",source="printed control",
                                  matrix=np.eye(4).tolist()))
            doc.saveas(drawing)
            for spec in specs:spec["source_sha256"]=fingerprint(drawing)
            profile=base/"reg.json";profile.write_text(json.dumps(dict(regions=[dict(id="test",frame_evidence="printed datum",
                                            curves=specs,stations_m=[0.,1.,3.])])))
            out=base/"result";r=run(src,out,curve_profile=profile)
            self.assertEqual(verify(out),r)
            self.assertEqual(r["hull"]["status"],"partial")
            self.assertEqual(r["hull"]["whole_hull"]["status"],"blocked")
            asset,=r["hull"]["patches"]
            self.assertFalse(read_meta(out/asset["file"])["formal_calculation_authorized"])
            self.assertIn("strict_delivery",[f["role"] for f in r["files"] if f["path"]==asset["file"]])
