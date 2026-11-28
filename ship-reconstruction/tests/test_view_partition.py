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


if __name__ == "__main__":
    unittest.main()
