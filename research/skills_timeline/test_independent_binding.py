"""Independent review probes; FakeCore only, no real W2 transport."""
import unittest
from copy import deepcopy
from dataclasses import replace
import test_provenance
from preview import Rejected

class IndependentTests(unittest.TestCase):
    def setUp(self):
        self.t=test_provenance.BindingTests();self.t.setUp()
    def test_mixed_valid_invalid_all_rejected(self):
        bad=deepcopy(self.t.conflict);bad['conflictId']='C-02';bad['b']['sourceLabel']='unknown'
        self.t.entries.append(bad)
        with self.assertRaises(Rejected):self.t.run_preview()
    def test_500_entries_limit(self):
        self.t.entries[:]=[dict(deepcopy(self.t.conflict),conflictId=f'C-{i:03}') for i in range(500)]
        self.assertEqual(len(self.t.run_preview()['candidates']),500)
        self.t.entries.append(dict(deepcopy(self.t.conflict),conflictId='C-500'))
        with self.assertRaises(Rejected):self.t.run_preview()
    def test_evidence_null_supported(self):
        self.t.conflict['a']['evidenceId']=None
        self.assertEqual(len(self.t.run_preview()['candidates']),1)
    def test_boolean_evidence_id_rejected(self):
        self.t.conflict['a']['evidenceId']=False
        with self.assertRaises(Rejected):self.t.run_preview()
    def test_recheck_requires_true_not_one(self):
        self.t.repo.recheck=lambda *a:1
        with self.assertRaises(Rejected):self.t.run_preview()
    def test_snapshot_fields_are_repository_values(self):
        self.t.conflict['a'].update(revision='forged',digest='forged',locator='forged')
        a=self.t.run_preview()['candidates'][0]['a']
        self.assertEqual(a['revision'],'r1');self.assertEqual(a['locator'],'fixture:1')
        self.assertNotEqual(a['digest'],'forged')
    def test_nested_output_not_aliased(self):
        out=self.t.run_preview();out['candidates'][0]['a']['locator']='changed'
        self.assertEqual(out['sources'][0]['locator'],'fixture:1')
    def test_locator_budget(self):
        self.t.repo.records['A']=replace(self.t.repo.records['A'],locator='x'*2049)
        with self.assertRaises(Rejected):self.t.run_preview()

if __name__=='__main__':unittest.main()
