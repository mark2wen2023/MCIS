import unittest
from dataclasses import replace,FrozenInstanceError
from timeline import *
S=Source('case','source','v1','page 1')
def event(id='a',**kw): return Event(id,S,'clock','original wording','point',**({'start':'10','end':'10'}|kw))
def corr(**kw): return Correction(**({'case':'case','clock':'clock','revision':'c1','offset':'0','uncertainty':'0','basis':(S,),'status':'confirmed'}|kw))
class Tests(unittest.TestCase):
 def test_point(self): self.assertTrue(validate_events([event()]))
 def test_range(self): self.assertTrue(validate_events([replace(event(),kind='range',end='12')]))
 def test_no_fake_precision(self): self.assertEqual(compare(event(),event('b',start='20',end='20')),'undetermined')
 def test_before(self): self.assertEqual(compare(event(),event('b',start='20',end='20'),corr(),corr()),'before')
 def test_after(self): self.assertEqual(compare(event(start='30',end='30'),event('b'),corr(),corr()),'after')
 def test_overlap_not_same(self): self.assertEqual(compare(event(),event('b'),corr(),corr()),'overlap-not-identity')
 def test_uncertainty(self): self.assertEqual(compare(event(),event('b',start='12',end='12'),corr(uncertainty='3'),corr()),'overlap-not-identity')
 def test_proposal_not_applied(self): self.assertEqual(interval(event(),corr(offset='100',status='proposed'))[:3],(Decimal(10),Decimal(10),False))
 def test_immutable(self):
  e=event();interval(e,corr(offset='3'))
  self.assertEqual(e.start,'10')
  with self.assertRaises(FrozenInstanceError): e.start='1'
 def test_correction_scope(self):
  for c in [corr(case='other'),corr(clock='other'),corr(basis=()),corr(uncertainty='-1')]:
   with self.assertRaises(ValueError): interval(event(),c)
 def test_relative_no_time(self):
  r=Event('r',S,'','after a','relative',after=('a',))
  self.assertTrue(validate_events([event(),r]));self.assertIsNone(interval(r))
 def test_cycle(self):
  with self.assertRaises(ValueError): validate_events([replace(event(),before=('b',)),event('b',before=('a',))])
 def test_missing_reference(self):
  with self.assertRaises(ValueError): validate_events([event(before=('missing',))])
 def test_crosscase(self):
  with self.assertRaises(ValueError): compare(event(),replace(event('b'),source=replace(S,case='other')))
 def test_invalid_numbers(self):
  for v in ['NaN','Infinity','-Infinity',True,'1e99']:
   with self.assertRaises(ValueError): interval(event(start=v,end=v))
 def test_bad_shape(self):
  for e in [event(end='9'),event(end='11'),replace(event(),kind='relative')]:
   with self.assertRaises(ValueError): validate_events([e])
 def test_duplicate(self):
  with self.assertRaises(ValueError): validate_events([event(),event()])
 def test_versions_remain(self):
  e=event();a=interval(e,corr());b=interval(e,corr(revision='c2',offset='3'))
  self.assertEqual(a[3],'c1');self.assertEqual(b[3],'c2');self.assertEqual(e.source.revision,'v1')
 def test_reject_excess_precision_instead_of_rounding(self):
  for value in ['1.0000000001','0.1234567890123456789012345678901',
                '0.1234567890123456789012345678902']:
   with self.assertRaises(ValueError): interval(event(start=value,end=value),corr())
 def test_nanosecond_difference_survives_zero_correction(self):
  a='999999999999.123456788'; b='999999999999.123456789'
  self.assertEqual(compare(event(start=a,end=a),event('b',start=b,end=b),corr(),corr()),'before')
 def test_arithmetic_independent_of_caller_context(self):
  from decimal import localcontext, Inexact, Rounded
  with localcontext() as ctx:
   ctx.prec=3;ctx.traps[Inexact]=True;ctx.traps[Rounded]=True
   a='999999999999.123456788';b='999999999999.123456789'
   self.assertEqual(compare(event(start=a,end=a),event('b',start=b,end=b),corr(),corr()),'before')
   self.assertEqual(interval(event(start=a,end=a),corr(offset='0.000000001'))[0],Decimal(b))
 def test_fixed_point_grammar(self):
  for value in ['1e-9',' 1','1 ','+1','01','1_0','１','.1','1.']:
   with self.assertRaises(ValueError): number(value)
 def test_precision_applies_to_corrections(self):
  for correction in [corr(offset='0.0000000001'),corr(uncertainty='0.0000000001')]:
   with self.assertRaises(ValueError): interval(event(),correction)
 def test_bounds_and_expansion(self):
  self.assertEqual(number('-1000000000000'),Decimal('-1000000000000'))
  with self.assertRaises(ValueError): number('1000000000000.000000001')
  self.assertEqual(interval(event(start='1000000000000',end='1000000000000'),
                           corr(offset='1000000000000',uncertainty='1000000000000'))[:2],
                   (Decimal('1000000000000'),Decimal('3000000000000')))
if __name__=='__main__': unittest.main()
