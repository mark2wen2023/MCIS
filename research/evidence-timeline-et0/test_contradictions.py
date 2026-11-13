import unittest
from timeline import Source, Event, Correction
from scoped import Scope, ScopedCorrection
from contradictions import direct_candidates

S1=Source('case','a','v1','p1')
S2=Source('case','b','v2','p2')
def event(id, source, lo, hi=None, **kw):
    return Event(id,source,'clock','original','point' if hi is None else 'range',lo,lo if hi is None else hi,**kw)
def sel(source, rev='c1', offset='0', unc='0', basis='case epoch', status='confirmed'):
    return ScopedCorrection(Correction('case','clock',rev,offset,unc,(source,),status),Scope(source,'-100','100'),basis)

class CandidateTests(unittest.TestCase):
    def test_reverse_order_candidate_and_provenance(self):
        a=event('a',S1,'10',before=('b',)); b=event('b',S2,'5')
        r=direct_candidates([a,b],{'a':sel(S1),'b':sel(S2,'c2')})
        self.assertEqual(len(r),1)
        self.assertEqual((r[0].before_id,r[0].after_id,r[0].before_source,r[0].after_source,r[0].before_calibration_revision,r[0].after_calibration_revision),('a','b',S1,S2,'c1','c2'))
        self.assertEqual(a.start,'10'); self.assertEqual(a.original_text,'original')
    def test_equal_instant_impossible_for_strict_before(self):
        self.assertEqual(len(direct_candidates([event('a',S1,'1',before=('b',)),event('b',S2,'1')],{'a':sel(S1),'b':sel(S2)})),1)
    def test_overlapping_or_possible_order_is_not_candidate(self):
        a=event('a',S1,'0','10',before=('b',));b=event('b',S2,'5','12')
        self.assertEqual(direct_candidates([a,b],{'a':sel(S1),'b':sel(S2)}),())
    def test_uncertainty_can_make_order_possible(self):
        a=event('a',S1,'10',before=('b',));b=event('b',S2,'9')
        self.assertEqual(direct_candidates([a,b],{'a':sel(S1,unc='1'),'b':sel(S2,unc='1')}),())
    def test_unaligned_proposed_or_other_basis_unresolved(self):
        a=event('a',S1,'10',before=('b',));b=event('b',S2,'5')
        for s in ({'a':sel(S1)}, {'a':sel(S1,status='proposed'),'b':sel(S2)}, {'a':sel(S1),'b':sel(S2,basis='other')}):
            self.assertEqual(direct_candidates([a,b],s),())
    def test_relative_is_unresolved_and_rejects_selection(self):
        a=Event('a',S1,'','original','relative',before=('b',));b=event('b',S2,'5')
        self.assertEqual(direct_candidates([a,b],{'b':sel(S2)}),())
        with self.assertRaises(ValueError): direct_candidates([a,b],{'a':sel(S1)})
    def test_reciprocal_declarations_deduplicated(self):
        a=event('a',S1,'10',before=('b',));b=event('b',S2,'5',after=('a',))
        self.assertEqual(len(direct_candidates([a,b],{'a':sel(S1),'b':sel(S2)})),1)
    def test_no_transitive_claim(self):
        a=event('a',S1,'10',before=('b',));b=Event('b',S1,'','middle','relative',before=('c',));c=event('c',S2,'5')
        self.assertEqual(direct_candidates([a,b,c],{'a':sel(S1),'c':sel(S2)}),())
    def test_bad_scope_and_unknown_selection_rejected(self):
        a=event('a',S1,'10',before=('b',));b=event('b',S2,'5')
        with self.assertRaises(ValueError): direct_candidates([a,b],{'a':sel(S2)})
        with self.assertRaises(ValueError): direct_candidates([a,b],{'z':sel(S1)})
    def test_cycle_rejected_not_silently_resolved(self):
        a=event('a',S1,'10',before=('b',)); b=event('b',S2,'5',before=('a',))
        with self.assertRaises(ValueError): direct_candidates([a,b],{'a':sel(S1),'b':sel(S2)})

if __name__=='__main__': unittest.main()
