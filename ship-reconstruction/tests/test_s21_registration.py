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
