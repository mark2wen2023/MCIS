import math
import sys
from pathlib import Path
import unittest
import ezdxf
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from s2lib import cad,view_registration

class Registration(unittest.TestCase):
    def test_rotated_reflected_native_station_ruler(self):
        for sign in [-1,1]:
            t=math.radians(32)
            a=np.array([[math.cos(t)*sign,-math.sin(t)],[math.sin(t)*sign,math.cos(t)]])
            def pos(x,y):return tuple(a@np.array([x,y])+[37,19])
            doc=ezdxf.new();m=doc.modelspace()
            for i in range(7):
                m.add_line(pos(i*3,-1),pos(i*3,4))
                m.add_text(str(i),dxfattribs={'insert':pos(i*3,-1.5),'height':.4})
            for i,s in enumerate(('WL2','WL4','Sheer','Units:mm','Units:inch')):
                m.add_text(s,dxfattribs={'insert':pos(2*i,3),'height':.4})
            d=view_registration.inspect(cad.read(doc),dict(source_sha256='test',insertion_units_code=0),[],[])
            layout=d['layouts'][0]
            self.assertEqual(layout['unit']['state'],'conflict')
            self.assertEqual(layout['ranked'][0]['view'],'XY')
            self.assertIsNone(layout['ranked'][0]['axes_m'])
            coef=layout['series']['station']['paper_to_label']
            self.assertAlmostEqual(np.dot(coef,[*pos(7.5,0),1]),2.5,places=3)
            self.assertFalse(d['installation_authorized'])

    def test_station_numbers_without_view_evidence(self):
        doc=ezdxf.new();m=doc.modelspace()
        for i in range(5):
            m.add_line((i*10,0),(i*10,10))
            m.add_text(str(i),dxfattribs={'insert':(i*10,-1)})
        r=view_registration.inspect(cad.read(doc),dict(source_sha256='test',insertion_units_code=0),[],[])
        self.assertFalse(r['layouts'][0]['ranked'])
