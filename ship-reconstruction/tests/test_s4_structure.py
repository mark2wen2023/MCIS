import json
from pathlib import Path
import sys
import tempfile
import unittest

import ezdxf
import trimesh

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import s4_structure as s4
from geometry import exchange
from unittest.mock import patch


def specimen(dest,role,missing=False,wrong=False,linked=True):
    for side in (False,True):
        doc=ezdxf.new()
        m=doc.modelspace()
        def text(x,y,s):m.add_text(s,dxfattribs={"insert":(x,y),"height":.01})
        if linked:text(-1,-1,"DRAWING ID=profiles" if side else "REF=profiles")
        for i,(x,y) in enumerate([(-2,-2),(5,-2),(5,5),(-2,5)]):
            xyz=(x,0,y) if side else (x,y,0)
            text(x,y,f"CONTROL C{i} X={xyz[0]} Y={xyz[1]} Z={xyz[2]} m")
        top=(.25 if wrong else .20) if side else 2
        m.add_lwpolyline([(0,0),(3,0),(3,top),(0,top)],close=True)
        text(.1,.1,"PART P1 "+role)
        if not side:
            if not missing:text(.1,.5,("HEIGHT" if role in ("tank","compartment") else "THICKNESS")+"=0.2 m")
            text(.1,.8,"NORMAL=+Z")
        doc.saveas(dest/("side.dxf" if side else "plan.dxf"))


class Structure(unittest.TestCase):
    def trial(self,role,**options):
        with tempfile.TemporaryDirectory() as td:
            dest=Path(td)
            specimen(dest,role,**options)
            mesh=trimesh.creation.box(extents=[3,2,1])
            mesh.apply_translation([1.5,1,.5])
            exchange(mesh).export(dest/"hull.glb")
            with patch.object(sys,"argv",["s4",str(dest),"--out",str(dest/"out"),"--hull-glb",str(dest/"hull.glb")]):
                code=s4.main()
            data=json.loads((dest/"out/structures.json").read_bytes())
            return code,data["components"][0],(dest/"out/P1.ply").exists()

    def test_all_supported_roles_and_hull_contact(self):
        for role in sorted(s4.ROLES):
            with self.subTest(role=role):
                code,r,file=self.trial(role)
                self.assertEqual((code,file),(0,True))
                self.assertAlmostEqual(r["quality"]["signed_volume_m3"],1.2)
                self.assertTrue(r["quality"]["closed_verified"])
                self.assertLess(r["hull_relation"]["min_distance_m"],1e-7)
                self.assertGreater(r["hull_relation"]["vertices_in_contact"],0)
                self.assertIn("joint_type",r["unknowns"])

    def test_missing_thickness(self):
        code,r,file=self.trial("deck",missing=True)
        self.assertEqual((code,file),(4,False))

    def test_unrelated_drawings(self):
        code,r,file=self.trial("deck",linked=False)
        self.assertEqual((code,file),(4,False))
        self.assertIn("missing_cross_sheet_reference",r["issues"])

    def test_second_view_disagrees(self):
        code,r,file=self.trial("tank",wrong=True)
        self.assertEqual((code,file),(4,False))
        self.assertAlmostEqual(r["second_view_error_m"],.05)

class NaturalPair(unittest.TestCase):
    def test_named_pair_and_second_view_extrusion_direction(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);specimen(root,"deck")
            for view in ("plan","side"):
                path=root/(view+".dxf");doc=ezdxf.readfile(path);ms=doc.modelspace()
                for e in list(ms.query("TEXT")):
                    text=e.dxf.text
                    if text=="PART P1 deck":e.dxf.text="主甲板 编号 D-5"+(" t=0.2 m" if view=="plan" else "")
                    if text.startswith(("THICKNESS","NORMAL")):ms.delete_entity(e)
                doc.saveas(path)
            with patch.object(sys,"argv",["s4",str(root),"--out",str(root/"out")]):self.assertEqual(s4.main(),0)
            result=json.loads((root/"out/structures.json").read_bytes())["components"][0]
            self.assertAlmostEqual(result["quality"]["signed_volume_m3"],1.2)
            self.assertTrue(any("normal_source" in r for r in result["sources"]))
