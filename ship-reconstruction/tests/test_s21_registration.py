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
