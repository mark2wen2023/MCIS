"""Synthetic envelope tests only. Does not run the real W2 executable."""
import unittest
from preview import preview, Rejected
from test_preview import Repository, FakeCore

class ImportQualityTests(unittest.TestCase):
    def run_result(self, extra):
        core = FakeCore()
        original = core.align
        def align(payload):
            result = original(payload)
            result['result'].update(extra)
            return result
        core.align = align
        return preview({'caseId': 'CASE-1', 'sourceIds': ['A', 'B'],
                        'caseEpochUtc': '2026-11-13T00:00:00Z'},
                       principal='fixture-investigator', repository=Repository(), core=core)

    def stats(self, **overrides):
        return dict(sourcesImported=2, tracks=2, linesRead=20, sentencesUsed=10, **overrides)

    def test_missing_statistics_unknown_not_clean(self):
        r = self.run_result({})
        self.assertEqual(r['importQuality']['state'], 'unknown')
        self.assertEqual(r['status'], 'needs_human_review')

    def test_positive_aggregate_counts_not_coverage_proof(self):
        q = self.run_result({'stats': self.stats()})['importQuality']
        self.assertEqual(q['state'], 'coverage_unverified')
        self.assertIs(q['perSourceCoverageVerified'], False)
        self.assertIs(q['timeOverlapVerified'], False)

    def test_no_usable_import_and_partial_import(self):
        for key, value in [('tracks', 0), ('tracks', 1), ('sentencesUsed', 0),
                           ('linesRead', 0), ('sourcesImported', 1)]:
            with self.subTest(key=key, value=value):
                stats = self.stats(); stats[key] = value
                self.assertEqual(self.run_result({'stats': stats})['importQuality']['state'],
                                 'insufficient_import')

    def test_reject_invalid_statistics(self):
        for value in [True, -1, 1.0, '2', 2**31, None]:
            with self.subTest(value=value):
                stats = self.stats(); stats['tracks'] = value
                with self.assertRaises(Rejected): self.run_result({'stats': stats})

    def test_source_count_cannot_exceed_selected(self):
        stats = self.stats(); stats['sourcesImported'] = 3
        with self.assertRaises(Rejected): self.run_result({'stats': stats})

    def test_missing_counter_rejected(self):
        with self.assertRaises(Rejected): self.run_result({'stats': {}})

    def test_diagnostic_text_not_forwarded(self):
        r = self.run_result({'importDiagnostics': [{'message': 'PRIVATE RAW TEXT'}]})
        self.assertEqual(r['importQuality']['unverifiedDiagnosticCount'], 1)
        self.assertNotIn('PRIVATE RAW TEXT', str(r))

    def test_diagnostic_budget_and_type(self):
        for value in ['message', [{}] * 10001]:
            with self.assertRaises(Rejected): self.run_result({'importDiagnostics': value})

if __name__ == '__main__': unittest.main()
