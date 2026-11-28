import sys
from pathlib import Path
import unittest

import ezdxf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from s2lib import cad, view_registration


def ruling_group(msp, x0, x1, y, title=None):
    for x in range(x0, x1 + 1, 2):
        msp.add_line((x, y), (x, y + 10))
    if title:
        msp.add_text(title, dxfattribs={"insert": (x0, y + 12), "height": 1})


class ViewPartition(unittest.TestCase):
    def inspect(self, doc):
        return view_registration.inspect(
            cad.read(doc), {"source_sha256": "synthetic", "insertion_units_code": 0}, [], []
        )

    def test_mixed_layout_cross_line_and_frame_do_not_merge_views(self):
        doc = ezdxf.new()
        msp = doc.modelspace()
        ruling_group(msp, 0, 14, 0, "PLAN VIEW")
        ruling_group(msp, 30, 44, 0, "PROFILE VIEW")
        # Dimension-like extension spanning the whitespace between two views.
        msp.add_line((12, 5), (32, 5))
        msp.add_leader([(12, 7), (21, 7), (32, 7)], dxfattribs={"annotation_handle": "0"})
        # Sheet frame is retained separately and must not join the view clusters.
        msp.add_line((-5, -5), (50, -5))
        result = self.inspect(doc)
        layout = result["layouts"][0]
        self.assertEqual(len(layout["regions"]), 2)
        self.assertEqual(len({r["region_id"] for r in layout["regions"]}), 2)
        cross = {h for r in layout["regions"] for h in r["shared_handles"]}
        self.assertTrue(cross)
        leader_handles = {x["instance"] for x in cad.read(doc)["leaders"]}
        self.assertTrue(leader_handles & cross)
        self.assertTrue(layout["drawing_frame_handles"])
        views = {r["view_type_candidates"][0]["view"] for r in layout["regions"]}
        self.assertEqual(views, {"XY", "XZ"})

    def test_overlapping_view_labels_are_reported_as_ambiguous(self):
        doc = ezdxf.new()
        msp = doc.modelspace()
        ruling_group(msp, 0, 14, 0)
        msp.add_text("PLAN VIEW", dxfattribs={"insert": (0, 12), "height": 1})
        msp.add_text("PROFILE VIEW", dxfattribs={"insert": (1, 12), "height": 1})
        region = self.inspect(doc)["layouts"][0]["regions"][0]
        views = {v["view"] for v in region["view_type_candidates"]}
        self.assertEqual(views, {"XY", "XZ"})
        self.assertEqual(region["overlap_status"], "multiple_view_titles_same_region")
        self.assertIn("view_type_requires_cross_view_or_title_confirmation", region["uncertainty"])

    def test_region_membership_and_ids_are_deterministic(self):
        doc = ezdxf.new()
        msp = doc.modelspace()
        ruling_group(msp, 0, 14, 0, "PLAN VIEW")
        ruling_group(msp, 30, 44, 0, "SECTION VIEW")
        a = self.inspect(doc)["layouts"][0]["regions"]
        b = self.inspect(doc)["layouts"][0]["regions"]
        self.assertEqual([r["region_id"] for r in a], [r["region_id"] for r in b])
        for r in a:
            self.assertTrue(r["handles"])
            self.assertTrue(all(isinstance(h, str) for h in r["handles"]))
            self.assertEqual(r["coordinate_space"], "source_layout_xy")

    def test_nearby_component_label_promotes_sparse_detail_candidate(self):
        doc = ezdxf.new()
        msp = doc.modelspace()
        msp.add_line((0, 0), (0, 8))
        msp.add_line((0, 8), (8, 8))
        msp.add_line((8, 0), (8, 8))
        msp.add_text("FOREDECK", dxfattribs={"insert": (1, 10), "height": 1})
        regions = self.inspect(doc)["layouts"][0]["regions"]
        self.assertEqual(len(regions), 1)
        self.assertEqual(regions[0]["view_type_candidates"][0]["view"], "detail")

    def test_sparse_multi_contour_view_is_retained_without_a_title(self):
        doc=ezdxf.new();msp=doc.modelspace()
        msp.add_lwpolyline([(0,3),(10,5),(20,5),(30,3)])
        msp.add_lwpolyline([(0,1),(10,0),(20,0),(30,1)])
        for x in (5,15,25):msp.add_line((x,1.5),(x,3.5))
        regions=self.inspect(doc)["layouts"][0]["regions"]
        self.assertEqual(len(regions),1)
        self.assertEqual({v["view"] for v in regions[0]["view_type_candidates"]},{"XY","XZ","YZ"})
        self.assertGreaterEqual(regions[0]["evidence"]["seed_entity_count"],5)

    def test_zero_length_lines_do_not_hide_fragmented_hull_contours(self):
        doc=ezdxf.new();msp=doc.modelspace()
        for _ in range(30):msp.add_line((0,0),(0,0))
        # Two broken contours with short transverse ribs form a sparse view.
        for x in range(0,49,8):
            x1=min(x+8,50)
            msp.add_line((x,8),(x1,10 if x1<50 else 8))
            msp.add_line((x,2),(x1,0 if x1<50 else 2))
        for x in (8,16,24,32,40):msp.add_line((x,2),(x,8))
        result=self.inspect(doc)["layouts"][0]
        self.assertTrue(result["regions"])
        self.assertTrue(result["unassigned_handles"])
        self.assertEqual(len(result["unassigned_handles"]),30)
        self.assertGreaterEqual(result["regions"][0]["evidence"]["seed_entity_count"],10)

    def test_short_fragments_recover_as_tangent_continuous_chain(self):
        doc=ezdxf.new();msp=doc.modelspace()
        pts=[(0,0),(5,0.1),(10,0.4),(15,0.9),(20,1.6)]
        for a,b in zip(pts,pts[1:]):
            msp.add_line(a,b)
        entities=list(view_registration._spatial_entities(cad.read(doc)).values())
        chains=view_registration._fragment_chains(entities,.15)
        self.assertEqual(len(chains),1)
        self.assertEqual(chains[0]['segment_count'],4)
        self.assertEqual(len(chains[0]['handles']),4)
        self.assertLess(chains[0]['max_tangent_turn_deg'],15)

    def test_right_angle_junction_is_not_joined_as_a_smooth_chain(self):
        doc=ezdxf.new();msp=doc.modelspace()
        for a,b in zip(((0,0),(5,0),(10,0),(10,5),(10,10)),((5,0),(10,0),(10,5),(10,10),(10,15))):
            msp.add_line(a,b)
        entities=list(view_registration._spatial_entities(cad.read(doc)).values())
        chains=view_registration._fragment_chains(entities,.01)
        self.assertEqual(len(chains),1)
        self.assertEqual(chains[0]['segment_count'],3)
        self.assertEqual(chains[0]['span'][0],0)
        self.assertEqual(chains[0]['span'][1],15)

    def test_view_scores_expose_outline_baseline_and_station_features(self):
        chains=[dict(segment_count=4,aspect_ratio=12,major_axis=[1,0],span=[20,2],
                     total_length=21,max_tangent_turn_deg=8,bounds=[0,y,20,y+.2],
                     points=[[0,y],[20,y+.2]]) for y in (0,3)]
        texts=[dict(n=f'fr{i}',text=f'Fr.{i}',p=[float(i),1,0]) for i in range(3)]
        texts.append(dict(n='baseline',text='BASELINE',p=[0,0,0]))
        scores=view_registration._view_feature_scores(chains,texts,[-1,-1,21,5])
        self.assertEqual(scores[0]['view'],'XZ')
        self.assertEqual(scores[0]['score_kind'],'ordinal_geometry_evidence')
        self.assertEqual(scores[0]['features']['station_label_count'],3)
        self.assertEqual(scores[0]['features']['baseline_label_count'],1)
        self.assertGreater(scores[0]['features']['paired_outline_score'],.9)


if __name__ == "__main__":
    unittest.main()
