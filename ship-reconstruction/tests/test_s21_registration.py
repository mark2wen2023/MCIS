import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from s2lib.intersections import section_envelope


class Intersections(unittest.TestCase):
    def test_rational_flat_span_interior_width(self):
        curve = {"geometry":{"control_points":[[1,0,0],[4,0,0],[1,0,0]],"degree":2,"knots":[0,0,0,1,1,1],"weights":[1,2,1]}}
        result = section_envelope(curve, {"Y":[1,0,0],"Z":[0,1,0]}, [0,1])
        self.assertAlmostEqual(result[0],3)
        self.assertNotIn(1,result)

    def test_tangent_without_crossing(self):
        curve = {"geometry":{"control_points":[[-1,1,0],[0,-1,0],[1,1,0]],"degree":2,"knots":[0,0,0,1,1,1],"weights":[]}}
        self.assertAlmostEqual(section_envelope(curve,{"Y":[1,0,3],"Z":[0,1,0]},[0])[0],3)

class RegistrationEvidence(unittest.TestCase):
    def test_uncertain_deck_does_not_change_raw_evidence(self):
        from s2lib.contract import fields
        h="a"*64
        t=dict(source_sha256=h,cells=[dict(instances=["D"],status="numeric",field_label="deck",value_m=2.3,station_m=3)],height_unit_check={"observations":[dict(value_instances=["D"],curve="C",geometry_height_m=2.0)]})
        result=fields(dict(inventory=[dict(source_sha256=h,registration_notes=[])],curves=[],issues=[],tables=[t]))
        self.assertAlmostEqual(result["conflicts"][0]["residual_m"],-.3)
        self.assertEqual(result["modeling_admission"]["blocked_regions"][0]["scope"],"deck_to_section_join")
        self.assertEqual(t["cells"][0]["value_m"],2.3)

    def test_local_side_labels_have_no_cross_sheet_authority(self):
        from s2lib.contract import drawing_notes,fields
        h="a"*64
        texts=[dict(handle="1",instance="1",layout="Model",p=[0,0,0],text="左燃油柜")]
        notes=drawing_notes(texts)
        f=fields(dict(inventory=[dict(source_sha256=h,registration_notes=notes)],curves=[],tables=[],issues=[]))
        self.assertEqual(f["uncertainties"][0]["scope"],"same_view_only")
        self.assertEqual(f["modeling_admission"]["state"],"blocked")

    def test_waterline_endpoint_roundoff(self):
        import numpy as np
        from s2lib.curves import hits
        self.assertEqual(list(hits(0,np.array([[4e-12,2.],[1.,4.]]))),[2])

class CrossDrawingMirror(unittest.TestCase):
    def test_two_signed_witnesses_and_contradiction(self):
        from s2lib.landmarks import decide
        a,b="a"*64,"b"*64
        labels=[dict(id=str(i),instance=str(i),layout="Model",p=[i,1,0]) for i in (1,2)]
        frame=dict(layout="Model",status="verified",controls=["1","2","3","4"],hull_halfspaces=[[1,0,-5],[-1,0,0],[0,1,-5],[0,-1,-5]],paper_to_ship_m=[[1,0,0],[0,1,0],[0,0,0]])
        m=lambda s:[[1,0,0],[0,s,0],[0,0,0]]
        c=dict(source_sha256=a,layout="Model",samples=[[0,1,0],[3,1,0]],ship_coordinate_candidates=[dict(y_sign=s,paper_to_ship_m=m(s)) for s in (-1,1)])
        import copy
        g=dict(inventory=[dict(source_sha256=a,landmarks=labels),dict(source_sha256=b,landmarks=copy.deepcopy(labels),registration_notes=[dict(instance="D",layout="Model",text="X forward Y port Z up origin: stern")])],relationships=[dict(explicit_refs=[1],sources=[a,b])],alignment=[dict(source_sha256=b,frames=[frame])],curves=[c])
        decide(g)
        self.assertEqual(c["registration_decision"]["y_sign"],1)
        g["inventory"][1]["landmarks"][1]["p"][1]=-1
        decide(g)
        self.assertIsNone(c["registration_decision"]["y_sign"])

class StationAssignment(unittest.TestCase):
    def test_native_outer_width_selects_supported_station(self):
        import numpy as np
        from s2lib.curves import offset_match
        curve={"type":"SPLINE","geometry":{"control_points":[[0,0,0],[2,0,0],[3,1,0],[4,2,0]],"degree":1,"knots":[0,0,1,2,3,3],"weights":[]}}
        cells=[dict(station_m=st,level_m=z,value_m=value,instances=[str((st,z))]) for st,vals in [(7,[2,3,4]),(8,[0,3.05,4])] for z,value in enumerate(vals)]
        frame={"view":"YZ","axes":{"Y":[1,0,0],"Z":[0,1,0]}}
        result=offset_match(frame,np.array([[0.,0],[2,0],[3,1],[4,2]]),cells,curve)
        self.assertEqual([v["fixed_m"] for v in result],[7,8])
        self.assertEqual(result[0]["rms_m"],0)
        self.assertEqual(result[0]["n"],3)
