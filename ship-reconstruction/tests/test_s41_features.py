import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import ezdxf
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from s2lib import cad
from s4lib.notes import parse
from s4lib.member_features import openings,spline_witness,tee_sections
from s4lib.installation import array_evidence
from s41_validate import check


class Features(unittest.TestCase):
    def test_rounded_hatch_positive_and_missing_side(self):
        doc=ezdxf.new(); m=doc.modelspace()
        m.add_text("hatch 12 x 8 m",dxfattribs={"insert":(6,4),"height":.15})
        for x,y,a,b in [(1,1,180,270),(11,1,270,360),(11,7,0,90),(1,7,90,180)]:m.add_arc((x,y),1,a,b)
        for a,b in [((1,0),(11,0)),((12,1),(12,7)),((1,8),(11,8))]:m.add_line(a,b)
        self.assertEqual(openings(cad.read(doc),"f"*64),[])
        m.add_line((0,1),(0,7))
        data=openings(cad.read(doc),"f"*64)
        self.assertEqual(len(data),1);self.assertFalse(data[0]["cap_authorized"])
        self.assertEqual(len(data[0]["evidence"]),9)
        m.add_line((0,1),(0,7))
        self.assertEqual(openings(cad.read(doc),"f"*64),[])

    def test_spline_endpoint_and_near_miss(self):
        c=dict(type="SPLINE",geometry=dict(degree=2,knots=[0,0,0,1,1,1],control_points=[[0,0],[1,1],[2,0]]))
        self.assertLess(spline_witness(c,np.array([1,.5]),1e-6)[0],1e-10)
        self.assertIsNone(spline_witness(c,np.array([1,.51]),1e-6))

    def test_explicit_phase_preserves_inference(self):
        s="FR.4~FR.16 肋骨，从Fr.4起每3肋距"
        q=array_evidence(dict(parse(s),text=s))
        self.assertEqual(q["inferred_frames"],[7,10,13,16])
        self.assertEqual(q["materialized_instances"],[])

    def test_tee_requires_geometric_join(self):
        def c(h,a,b):return dict(type="LINE",layout="Model",instance=h,samples=[a,b])
        curves={"w":c("w",[0,0],[0,18]),"f":c("f",[-4,18],[4,18])}
        row=dict(parse("T2x8/1x18"),instance="n",layout="Model",source_sha256="0"*64,
                 leaders=[{"handles":["e"],"target_instances":["w"]}])
        out=tee_sections(row,curves)
        self.assertEqual(len(out),1); self.assertIsNone(out[0]["installed_member"])
        curves["f"]=c("f",[-4,18.1],[4,18.1])
        self.assertEqual(tee_sections(row,curves),[])

    def test_replay_catches_modified_witness(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=ROOT/"benchmarks/s41-frame-scope/h01";out=Path(tmp)/"result"
            subprocess.run([sys.executable,str(ROOT/"scripts/s41.py"),str(src),"--out",str(out),"--mode","observe"],check=True)
            self.assertEqual(check(out,src),[])
            p=out/"evidence-graph.json";g=json.loads(p.read_bytes())
            g["arrays"][0]["phase"]=81
            p.write_text(json.dumps(g))
            self.assertTrue(check(out,src))
