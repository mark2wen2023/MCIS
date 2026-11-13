import unittest
from dataclasses import replace
from timeline import Source, Event, Correction
from scoped import Scope, ScopedCorrection, scoped_interval, scoped_compare

S = Source('case', 's', 'v1', 'page 1')
def event(id='a', start='10', end='10'):
    return Event(id,S,'clock','original','point' if start==end else 'range',start,end)
def selection(**changes):
    c = Correction('case','clock','c1','2','1',(S,),'confirmed')
    return replace(ScopedCorrection(c,Scope(S,'10','20'),'case-epoch-v1'),**changes)

class ScopedTests(unittest.TestCase):
    def test_boundaries_and_original_unchanged(self):
        e=event(start='10',end='20')
        self.assertEqual(tuple(map(str,scoped_interval(e,selection())[:2])),('11','23'))
        self.assertEqual((e.start,e.end),('10','20'))
    def test_partial_overlap_and_outside_refused(self):
        for e in (event(start='9',end='10'),event(start='20',end='21'),event(start='21',end='21')):
            with self.assertRaises(ValueError): scoped_interval(e,selection())
    def test_source_revision_and_locator_are_pinned(self):
        for s in (replace(S,revision='v2'),replace(S,locator='page 2'),replace(S,id='other')):
            with self.assertRaises(ValueError): scoped_interval(replace(event(),source=s),selection())
    def test_bad_scope_and_case(self):
        for scope in (Scope(S,'20','10'),Scope(replace(S,case='other'),'0','20')):
            with self.assertRaises(ValueError): scoped_interval(event(),selection(scope=scope))
    def test_proposed_not_applied_and_no_default_alignment(self):
        p=selection(); p=replace(p,correction=replace(p.correction,status='proposed'))
        self.assertFalse(scoped_interval(event(),p)[2])
        self.assertEqual(scoped_compare(event(),event('b',start='20',end='20'),p,selection()),'undetermined')
        self.assertEqual(scoped_compare(event(),event('b',start='20',end='20')),'undetermined')
    def test_relative_not_given_invented_time(self):
        r=Event('r',S,'','after a','relative',after=('a',))
        self.assertIsNone(scoped_interval(r))
        with self.assertRaises(ValueError): scoped_interval(r,selection())
    def test_uncertainty_and_temporal_order_only(self):
        self.assertEqual(scoped_compare(event(),event('b',start='20',end='20'),selection(),selection()),'before')
        self.assertEqual(scoped_compare(event(),event('b',start='10',end='10'),selection(),selection()),'overlap-not-identity')
    def test_legacy_compare_cannot_bypass_target_basis(self):
        from timeline import compare as legacy_compare
        with self.assertRaisesRegex(ValueError, 'unsafe legacy comparison disabled'):
            legacy_compare(event(),event('b',start='20',end='20'),selection().correction,selection().correction)
    def test_explicit_matching_target_basis_required(self):
        a=selection()
        for basis in ('', '  ', None):
            with self.assertRaises(ValueError): scoped_interval(event(),replace(a,target_basis=basis))
        b=replace(a,target_basis='case-epoch-v2')
        self.assertEqual(scoped_compare(event(),event('b',start='20',end='20'),a,b),'undetermined')
        self.assertEqual(scoped_compare(event(),event('b',start='20',end='20'),a,a),'before')
    def test_bad_clock_or_basis_rejected(self):
        s=selection()
        for c in (replace(s.correction,clock='other'),replace(s.correction,basis=())):
            with self.assertRaises(ValueError): scoped_interval(event(),replace(s,correction=c))

if __name__ == '__main__': unittest.main()
