import sys
import unittest
from pathlib import Path
import numpy as np
import ezdxf
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from s2lib import cad
from s4lib.annotations import LayoutIndex
from s4lib.panels import bounded_cells,solid

class LocalPlate(unittest.TestCase):
    def test_original_boundary_subsegment(self):
        d=ezdxf.new();m=d.modelspace()
        coords=[((0,-4),(0,10)),((0,3),(2,3)),((2,3),(2,2)),((2,2),(0,1))]
        for a,b in coords:m.add_line(a,b)
        c=cad.read(d)["curves"]
        out=bounded_cells(LayoutIndex(c,[]),np.array([.5,2]),4,set(),[])
        self.assertEqual(len(out),1);self.assertEqual(len(out[0]["boundary_handles"]),4)
        self.assertAlmostEqual(out[0]["area_wcs2"],3)
        _,m=solid(out[0]["contour_wcs"],.2,1)
        self.assertAlmostEqual(m.volume,.6)

    def test_artificial_clip_boundary_cannot_close_open_panel(self):
        d=ezdxf.new();m=d.modelspace()
        for a,b in [((0,-10),(0,10)),((0,0),(10,0)),((0,3),(10,3))]:m.add_line(a,b)
        self.assertEqual(bounded_cells(LayoutIndex(cad.read(d)["curves"],[]),np.array([1,1]),2,set(),[]),[])

    def test_different_points_on_one_shell_edge(self):
        from s4lib.annotations import target_conflicts
        def note(h,position,val):
            return dict(source_sha256="1"*64,instance=h,dimensions=[dict(kind="thickness",unit="mm",value=val)],leaders=[dict(target_instances=["E"],tip_wcs=position,tolerance_wcs=.01)])
        a=note("A",[0,0],8);b=note("B",[5,0],12)
        self.assertEqual(target_conflicts([a,b]),[])
        b["leaders"][0]["tip_wcs"]=[0,0]
        self.assertEqual(len(target_conflicts([a,b])),1)
