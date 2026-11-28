import math
import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from s2lib.view_registration import coordinate_controls,crosscheck


class CoordinateCandidates(unittest.TestCase):
    def texts(self, mirrored=False, unit='in'):
        theta=math.radians(31)
        rotation=np.array([[math.cos(theta),-math.sin(theta)],[math.sin(theta),math.cos(theta)]])
        reflection=np.diag([-1.,1.]) if mirrored else np.eye(2)
        transform=rotation@reflection
        rows=[]
        for i,(x,y) in enumerate(((0,0),(4,0),(0,5),(4,5),(2,2),(7,1))):
            p=transform@np.array([x,y])+[23.,-14.]
            q=np.array([x*.3048+1.2,y*.3048-.7])
            rows.append(dict(layout='Model',instance=f'h{i}',p=[*p,0],text=f'X={q[0]/.0254:.5f}, Y={q[1]/.0254:.5f} in'))
        # A nearby but incorrect annotation must be rejected as an outlier.
        rows.append(dict(layout='Model',instance='bad',p=[* (transform@np.array([3.,4.])+[23.,-14.]),0],text='X=999, Y=-888 in'))
        return rows

    def geometric_links(self, texts):
        leaders=[];segments=[]
        for t in texts:
            p=t['p']
            leaders.append(dict(layout='Model',instance='L'+t['instance'],annotation=t['instance'],
                                vertices=[p,[p[0]+.5,p[1]+.5,0]]))
            segments.append(dict(layout='Model',instance='G'+t['instance'],a=p,b=[p[0]+.1,p[1],0]))
        return leaders,segments

    def test_rotated_and_mirrored_candidates_keep_parity_and_holdout(self):
        bounds=[-100,-100,100,100]
        for mirrored,expected in ((False,'unmirrored'),(True,'mirrored')):
            texts=self.texts(mirrored);leaders,segments=self.geometric_links(texts)
            result=coordinate_controls(texts,bounds,'R1',leaders,segments)[0]
            self.assertEqual(result['status'],'candidate')
            self.assertEqual(result['parity'],expected)
            self.assertEqual(result['inlier_count'],6)
            self.assertEqual(result['rejected_handles'],['bad'])
            self.assertEqual(len(result['leave_one_out_errors_m']),6)
            self.assertLess(result['max_holdout_residual_m'],1e-5)
            self.assertIn('vessel_axis_orientation',result['unknown'])

    def test_coordinate_without_explicit_unit_is_not_scaled(self):
        rows=[dict(layout='Model',instance=str(i),p=[x,y,0],text=f'X={x}, Y={y}')
              for i,(x,y) in enumerate(((0,0),(1,0),(0,1),(1,1)))]
        self.assertEqual(coordinate_controls(rows,[-1,-1,2,2],'R2'),[])

    def test_text_insertion_anchor_is_never_treated_as_geometric_control(self):
        texts=self.texts()
        result=coordinate_controls(texts,[-100,-100,100,100],'R2')[0]
        self.assertEqual(result['status'],'annotation_only_unverified')
        self.assertIsNone(result['paper_to_printed_xy_m'])
        self.assertIn('no_coordinate_transform',result['unknown'])

    def test_fewer_than_four_points_cannot_claim_a_transform(self):
        rows=self.texts()[:3]
        leaders,segments=self.geometric_links(rows)
        result=coordinate_controls(rows,[-100,-100,100,100],'R3',leaders,segments)
        self.assertEqual(result[0]['status'],'insufficient_geometric_controls')

    def test_weak_consensus_remains_low_confidence(self):
        rows=self.texts()[:4]
        for i,(x,y) in enumerate(((2,3),(7,4),(5,8))):
            rows.append(dict(layout='Model',instance=f'bad{i}',p=[x,y,0],text=f'X={x*31}, Y={y*27} in'))
        leaders,segments=self.geometric_links(rows)
        result=coordinate_controls(rows,[-100,-100,100,100],'R4',leaders,segments)[0]
        self.assertEqual(result['status'],'low_confidence_candidate')
        self.assertEqual(result['confidence'],'low')

    def test_cross_view_common_stations_compare_relative_paper_scale(self):
        def region(rid,scale):
            return dict(region_id=rid,registration=dict(series={'station':dict(
                paper_to_label=[scale,0,0],ticks=[dict(value=x) for x in (0,1,2)])}))
        docs=[]
        for source,rid,scale in [('a','R1',2.),('b','R2',2.004)]:
            docs.append(dict(source_sha256=source,layouts=[dict(layout='Model',series={},regions=[region(rid,scale)],ranked=[])]))
        result=crosscheck(docs)
        check=next(x for x in result if x['kind']=='region_shared_label_scale')
        self.assertEqual(check['common_labels'],[0,1,2])
        self.assertTrue(check['equal_paper_pitch'])
        self.assertFalse(check['metric_authorization'])


if __name__=='__main__':unittest.main()
