"""Independent real-W2 probes; fictional sources, synthetic repository identity."""
import unittest
import test_real_w2 as real
from test_real_w2 import DOTNET, DLL, fixture

@unittest.skipUnless(DOTNET and DLL, 'requires built real W2')
class IndependentRealW2(unittest.TestCase):
    def setUp(self):
        self.h = real.RealW2Tests()
        self.h.setUp()

    def test_circular_heading_wrap_is_not_false_conflict(self):
        self.h.source('A', fixture(359.5))
        self.h.source('B', fixture(0.5))
        r=self.h.run_preview()
        self.assertEqual(r['candidates'], [])
        self.assertEqual(r['importQuality']['state'], 'coverage_unverified')
        self.assertEqual(self.h.core.last['result']['stats']['sentencesUsed'],6)

    def test_source_selection_order_keeps_identity(self):
        self.h.request['sourceIds']=['B','A']
        r=self.h.run_preview()
        c=r['candidates'][0]
        self.assertEqual({c['a']['sourceId'],c['b']['sourceId']},{'A','B'})
        for side in ('a','b'):
            self.assertEqual(c[side]['digest'],self.h.repo.records[c[side]['sourceId']].digest)

    def test_missing_log_timestamp_does_not_become_valid_coverage(self):
        self.h.source('A', '\n'.join(l.split(' ',1)[1] for l in fixture(90).splitlines()))
        self.h.source('B', '\n'.join(l.split(' ',1)[1] for l in fixture(110).splitlines()))
        r=self.h.run_preview()
        self.assertEqual(r['importQuality']['state'],'insufficient_import')
        self.assertEqual(r['candidates'],[])

    def test_source_record_timezone_normalizes_real_overlap(self):
        self.h.source('B',fixture(110).replace('T00:00:', 'T08:00:').replace('Z ', '+08:00 '))
        r=self.h.run_preview()
        self.assertEqual(len(r['candidates']),1)
        self.assertEqual(self.h.core.last['result']['conflicts'][0]['delta'],20)
        self.assertIn('timezone_of_source_records',r['notChecked'])
