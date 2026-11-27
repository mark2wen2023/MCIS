"""可公开的控制变量；独立陌生图另存，不与此开发夹具混用。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from s4lib.installation import project_section, array_evidence
from s4lib.notes import parse


def fixture():
    def note(h, s, x, y):
        return dict(handle=h,instance=h,layout="Model",text=s,p=[x,y,0.],height=.2,baseline=[1.,0.,0.])
    def line(h, a, b):
        return dict(handle=h,instance=h,layout="Model",type="LINE",samples=[a,b])
    data=dict(texts=[note("t0","20",0,-.25),note("t1","25",5,-.25),note("t2","30",10,-.25),
                     note("l","BL",-1,0.02),note("r","BL",11,0.02),note("s","纵剖面",5,3)],
              curves=[line("left",[-1.5,0],[0,0]),line("base",[0,0],[10,0]),line("right",[10,0],[11.5,0]),
                      line("a",[0,0],[0,-.1]),line("b",[5,0],[5,-.1]),line("c",[10,0],[10,-.1]),
                      line("side",[5,0],[5,2])])
    model=dict(scale=dict(m_per_drawing_unit=1.,handles=["t0","t1","t2","pitch"]),
               frame_attachment=dict(grid_handles=["a","b","c"],label_handles=["t0","t1","t2"],boundary_handles=["side"],frame_number=25),
               contour=dict(contour_wcs=[[5,1],[5.1,1],[5.1,1.5],[5,1.5]]))
    return data,model


class Installation(unittest.TestCase):
    def test_frame_positive_and_missing_y(self):
        d,m=fixture(); q=project_section(d,m,"Model")
        self.assertEqual(q["status"],"partial_xz")
        self.assertAlmostEqual(q["vertices_dx_z_m"][2][0],.1)
        self.assertAlmostEqual(q["vertices_dx_z_m"][2][1],1.5)
        self.assertIsNone(q["ship_y_m"])
        self.assertIsNone(q["signed_thickness_direction"])

    def test_disconnected_datum(self):
        d,m=fixture(); d["curves"][1]["samples"]=[[.3,0],[10,0]]
        self.assertNotEqual(project_section(d,m,"Model")["status"],"partial_xz")

    def test_wrong_view_and_missing_support(self):
        d,m=fixture(); d["texts"][-1]["text"]="甲板平面图"
        self.assertNotEqual(project_section(d,m,"Model")["status"],"partial_xz")
        d,m=fixture(); m["frame_attachment"]=None
        self.assertNotEqual(project_section(d,m,"Model")["status"],"partial_xz")

    def test_range_is_not_an_array(self):
        q=array_evidence(parse("FR.3~FR.9 肋骨"))
        self.assertEqual(q["explicit_frames"],[])
        self.assertEqual(q["inferred_frames"],[])
        self.assertEqual(len(q["intervals"]),1)

    def test_singular_and_phase(self):
        q=array_evidence(parse("FR.3 FR.5 FR.7 肋骨"))
        self.assertEqual(q["explicit_frames"],[3,5,7])
        self.assertEqual(q["inferred_frames"],[])
        q=array_evidence(parse("肋骨 隔肋设"))
        self.assertIsNone(q["phase"])
        self.assertEqual(q["inferred_frames"],[])
