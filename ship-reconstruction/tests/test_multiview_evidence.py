import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from geometry import build_shell
class Evidence(unittest.TestCase):
    def test_consistent_views_retained(self):
        rows=[dict(x_m=x,z_m=z,breadth_m=None) for x in (0,1) for z in (0,1)]
        curves=[dict(kind='waterline',use='constraint',handle=f'w{z}',points_m=[[0,1,z],[1,1,z]]) for z in (0,1)]
        curves.append(dict(kind='section',use='constraint',handle='s0',points_m=[[0,1,0],[0,1,1]]))
        _,faces,detail=build_shell(rows,curves,False,False)
        self.assertTrue(all('s0' in f['handles'] for f in faces))
        self.assertEqual(detail['derived_values'][0]['handles'],['s0','w0'])
    def test_printed_value_retains_support(self):
        rows=[dict(x_m=x,z_m=z,breadth_m=1,handle=f'p{x}{z}') for x in (0,1) for z in (0,1)]
        curves=[dict(kind='waterline',use='constraint',handle=f'w{z}',points_m=[[0,1,z],[1,1,z]]) for z in (0,1)]
        _,faces,_=build_shell(rows,curves,False,False)
        self.assertTrue(all('w0' in f['handles'] and 'w1' in f['handles'] for f in faces))
