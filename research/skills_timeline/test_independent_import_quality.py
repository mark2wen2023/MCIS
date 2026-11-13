"""Independent adversarial tests. Fakes only; no real W2/runtime coverage."""
import unittest
from preview import _import_quality, Rejected


class IndependentImportQuality(unittest.TestCase):
    def test_all_zero_is_insufficient_not_clear(self):
        q = _import_quality({'stats': dict(sourcesImported=0, tracks=0,
                                          linesRead=0, sentencesUsed=0)}, 2)
        self.assertEqual(q['state'], 'insufficient_import')
        self.assertFalse(q['perSourceCoverageVerified'])

    def test_each_counter_rejects_bool(self):
        base = dict(sourcesImported=2, tracks=2, linesRead=2, sentencesUsed=2)
        for key in base:
            with self.subTest(key=key), self.assertRaises(Rejected):
                _import_quality({'stats': {**base, key: True}}, 2)

    def test_extra_fields_and_diagnostic_payload_not_relayed(self):
        q = _import_quality({'stats': dict(sourcesImported=2, tracks=2,
                                          linesRead=2, sentencesUsed=2,
                                          proof='DO NOT RELAY'),
                             'importDiagnostics': ['DO NOT RELAY']}, 2)
        self.assertNotIn('DO NOT RELAY', str(q))
        self.assertEqual(q['unverifiedDiagnosticCount'], 1)
        self.assertEqual(q['state'], 'coverage_unverified')

    def test_null_statistics_stays_unknown(self):
        q = _import_quality({'stats': None, 'importDiagnostics': []}, 2)
        self.assertEqual(q['state'], 'unknown')
        self.assertIsNone(q['unverifiedCoreCounts'])
        self.assertEqual(q['unverifiedDiagnosticCount'], 0)

    def test_diagnostic_limit_is_inclusive(self):
        q = _import_quality({'importDiagnostics': [None] * 10000}, 2)
        self.assertEqual(q['unverifiedDiagnosticCount'], 10000)

    def test_aggregate_cannot_certify_two_sources(self):
        # The two tracks may both belong to one source; retain uncertainty.
        q = _import_quality({'stats': dict(sourcesImported=2, tracks=2,
                                          linesRead=20, sentencesUsed=10)}, 2)
        self.assertEqual(q['state'], 'coverage_unverified')
        self.assertFalse(q['timeOverlapVerified'])


if __name__ == '__main__': unittest.main()
