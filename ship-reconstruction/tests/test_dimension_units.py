import sys
from pathlib import Path
import unittest

import ezdxf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from s2lib import alignment, cad, view_registration


class ImperialAnnotations(unittest.TestCase):
    def test_fractional_and_mixed_imperial_lengths(self):
        cases = {
            '3/8"': .009525,
            '3 1/2 in': .0889,
            '3½"': .0889,
            "5'-6 1/2\"": 1.6891,
            '1 ft 6 in': .4572,
        }
        for label, expected_m in cases.items():
            with self.subTest(label=label):
                parsed = alignment.dimension_annotation(label)
                self.assertIsNotNone(parsed)
                self.assertAlmostEqual(parsed['values_m'][0], expected_m, places=7)
                self.assertEqual(parsed['source_text'], label)

    def test_pairs_scales_and_metric_units_are_distinguished(self):
        pair = alignment.dimension_annotation('94x30in')
        self.assertEqual(pair['kind'], 'dimension_pair')
        self.assertEqual(pair['values_m'], [2.3876, .762])
        scale = alignment.dimension_annotation('Scale: 1:48')
        self.assertEqual(scale['kind'], 'paper_scale')
        self.assertEqual(scale['denominator'], 48)
        metric = alignment.dimension_annotation('12 mm')
        self.assertEqual(metric['values_m'], [.012])

    def test_region_unit_evidence_stays_local_and_keeps_conflicts(self):
        doc = ezdxf.new()
        msp = doc.modelspace()
        for x in range(0, 15, 2):
            msp.add_line((x, 0), (x, 10))
        msp.add_text('Units: mm', dxfattribs={'insert': (0, 12), 'height': 1})
        msp.add_text('3/8"', dxfattribs={'insert': (4, 14), 'height': 1})
        for x in range(50, 65, 2):
            msp.add_line((x, 0), (x, 10))
        msp.add_text('Units: inches', dxfattribs={'insert': (50, 12), 'height': 1})
        msp.add_text('3 1/2"', dxfattribs={'insert': (54, 14), 'height': 1})
        data = cad.read(doc)
        result = view_registration.inspect(data, {'source_sha256': 'units', 'insertion_units_code': 0}, [], [])
        regions = result['layouts'][0]['regions']
        self.assertEqual(len(regions), 2)
        metric = next(r for r in regions if r['unit_evidence']['declared_units'] == ['mm'])
        imperial = next(r for r in regions if r['unit_evidence']['declared_units'] == ['in'])
        self.assertEqual(metric['unit_evidence']['state'], 'conflict')
        self.assertEqual(imperial['unit_evidence']['state'], 'evidenced')
        self.assertAlmostEqual(metric['dimensions'][0]['values_m'][0], .009525)
        self.assertAlmostEqual(imperial['dimensions'][0]['values_m'][0], .0889)
        self.assertNotEqual(metric['region_id'], imperial['region_id'])


if __name__ == '__main__':
    unittest.main()
