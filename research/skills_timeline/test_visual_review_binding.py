"""Tests record/source binding, NOT automated proof of image interpretation."""
import hashlib
import json
from pathlib import Path
import unittest


class VisualReviewBinding(unittest.TestCase):
    def setUp(self):
        self.root=Path(__file__).resolve().parents[2]
        self.review=json.loads((Path(__file__).parent/'public_report_visual_review.json').read_text())

    def test_original_public_pdf_is_bound_not_an_unverified_replacement(self):
        r=self.review['report']
        data=(self.root/r['path']).read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(),r['sha256'])
        self.assertEqual(hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),r['gitBlob'])

    def test_visual_records_preserve_same_identity_and_distinct_quantities(self):
        a,b=self.review['observations']
        self.assertEqual(a['imo'],b['imo'])
        self.assertEqual(a['imo'],'9958212')
        self.assertEqual((a['headingDeg'],b['headingDeg']), (47,48))
        self.assertEqual(a['courseDeg'],54)
        self.assertNotEqual(a['courseDeg'],a['headingDeg'])
        self.assertEqual(a['headingReference'],'not_explicit_in_crop')

    def test_no_silent_lmt_clock_correction_or_human_signoff(self):
        a,b=self.review['observations']
        self.assertEqual(b['displayTimeLmt'],b['displayTimeUtc'])
        self.assertEqual(b['interpretationBasis'],'explicit_UTC_field_not_LMT_field')
        self.assertEqual(self.review['investigatorApproval'],'pending')
        for key in ('originalTelemetryVerified','clockCalibrationVerified',
                    'independentEvidenceSourcesVerified'):
            self.assertIs(self.review[key],False)
