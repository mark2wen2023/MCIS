"""Synthetic policy tests: no service, DB, original Access or real receipt issuer."""
from dataclasses import FrozenInstanceError, replace
import importlib.util
from pathlib import Path
import sys
import unittest

spec = importlib.util.spec_from_file_location('pair_policy', Path(__file__).with_name('policy.py'))
p = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = p
spec.loader.exec_module(p)
CASE = 'SYN-PAIR-POLICY'
VESSELS = ('SYN-A', 'SYN-B')

def entries():
    return [{'vesselId': vessel, 'original': {'caseId': CASE, 'evidenceId': 'SYN-E-' + side,
             'requestDigest': digest * 64, 'sourceSha256': sha * 64}}
            for vessel, side, digest, sha in zip(VESSELS, ('A', 'B'), ('a', 'b'), ('c', 'd'))]

class Checks(unittest.TestCase):
    def setUp(self):
        self.raw = entries()
        self.v1 = p.freeze_pair(CASE, VESSELS, self.raw)
        self.receipt = p.GenerationReceipt('SYN-GENERATION-1', self.v1)

    def status(self, selected, receipt):
        return p.compare_versions(CASE, VESSELS, selected=selected, receipt=receipt)

    def test_exact_pair_current_and_immutable(self):
        self.assertEqual(self.status(self.v1, self.receipt), 'current')
        self.raw[0]['original']['sourceSha256'] = 'f' * 64
        self.assertEqual(self.status(self.v1, self.receipt), 'current')
        with self.assertRaises(FrozenInstanceError):
            self.receipt.inputs = None

    def test_a_new_version_b_fixed_old_receipt_historical(self):
        changed = entries()
        changed[0]['original'].update(evidenceId='SYN-E-A2', requestDigest='e'*64, sourceSha256='f'*64)
        v2 = p.freeze_pair(CASE, VESSELS, changed)
        self.assertEqual(v2.sources[1], self.v1.sources[1])
        self.assertEqual(self.status(v2, self.receipt), 'historical')
        self.assertEqual(self.status(v2, p.GenerationReceipt('SYN-GENERATION-2', v2)), 'current')
        self.assertEqual(self.receipt.inputs, self.v1)

    def test_each_identity_component_matters_even_equal_bytes(self):
        for key, value in [('evidenceId', 'SYN-E-A2'), ('requestDigest', 'e'*64), ('sourceSha256', 'f'*64)]:
            changed = entries();changed[0]['original'][key] = value
            with self.subTest(key=key):
                self.assertEqual(self.status(p.freeze_pair(CASE,VESSELS,changed), self.receipt), 'historical')

    def test_absent_selection_or_generation_unknown(self):
        for selected, receipt in [(None,None), (self.v1,None), (None,self.receipt)]:
            self.assertEqual(self.status(selected,receipt), 'unknown')
        # seedVerified/seedSha256 cannot substitute for a generation receipt.
        with self.assertRaises(p.InvalidBinding):
            self.status(self.v1, {'seedVerified':True,'seedSha256':'a'*64})

    def test_swapped_wrong_vessel_cross_case_rejected(self):
        variants = [list(reversed(entries()))]
        for key,value in [('vesselId','SYN-X'),('caseId','SYN-OTHER')]:
            bad=entries()
            if key=='vesselId':bad[0][key]=value
            else:bad[0]['original'][key]=value
            variants.append(bad)
        for bad in variants:
            with self.assertRaises(p.InvalidBinding):p.freeze_pair(CASE,VESSELS,bad)
        with self.assertRaises(p.InvalidBinding):
            p.compare_versions('SYN-OTHER',VESSELS,selected=self.v1,receipt=self.receipt)

    def test_malformed_and_duplicate_fail_closed(self):
        for value in [None, '', 'A'*64, 'a'*63, 7]:
            bad=entries();bad[0]['original']['sourceSha256']=value
            with self.assertRaises(p.InvalidBinding):p.freeze_pair(CASE,VESSELS,bad)
        for key in ['evidenceId','requestDigest']:
            bad=entries();bad[1]['original'][key]=bad[0]['original'][key]
            with self.assertRaises(p.InvalidBinding):p.freeze_pair(CASE,VESSELS,bad)
        for bad in [[],entries()[:1],entries()+entries()[:1]]:
            with self.assertRaises(p.InvalidBinding):p.freeze_pair(CASE,VESSELS,bad)
        bad=entries();bad[0]['original']['revision']=2
        with self.assertRaises(p.InvalidBinding):p.freeze_pair(CASE,VESSELS,bad)

    def test_receipt_is_revalidated_not_trusted_by_type(self):
        bad=p.GenerationReceipt('SYN-BAD',p.Pair((replace(self.v1.sources[0],case_id='SYN-OTHER'),self.v1.sources[1])))
        for selected in [None,self.v1]:
            with self.assertRaises(p.InvalidBinding):self.status(selected,bad)
        with self.assertRaises(p.InvalidBinding):self.status(p.Pair(()),None)
        with self.assertRaises(p.InvalidBinding):self.status(self.v1,replace(self.receipt,generation_id=''))

if __name__=='__main__':unittest.main(verbosity=2)
