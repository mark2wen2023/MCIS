"""Synthetic formal GISIS call; no application, database, seeds, or exports."""
from pathlib import Path
import copy
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'service'))
from mcis_service.reports.data_policy import data_status, is_fictional
from mcis_service.reports.gisis import build_gisis, validate_gisis

class Checks(unittest.TestCase):
    def test_formal_builder(self):
        case = {'caseId':'SYN-XREPO-001','isFictionalDemo':True,'deaths':0,'pollution':False}
        vessels = [{'vesselId':'SYN-A','name':'Synthetic A'}]
        before = copy.deepcopy((case,vessels))
        result = build_gisis(case,vessels)
        self.assertEqual(result['realDataStatus'],'fictional')
        self.assertIs(result['isFictionalDemo'],True)
        fields = {f['id']:f for f in result['fields']}
        self.assertEqual(fields['deaths']['value'],0)
        self.assertIs(fields['pollution']['value'],False)
        self.assertIsNone(fields['incidentTimeUtc']['value'])
        self.assertEqual(fields['incidentTimeUtc']['missingLabel'],'缺数据 / Missing data')
        self.assertFalse(validate_gisis(result)['valid'])
        self.assertEqual((case,vessels),before)

    def test_classification_keeps_strict_true(self):
        for flag, expected in [(True,'fictional'),(False,'pending-confirmation'),(1,'pending-confirmation'),(None,'pending-confirmation')]:
            with self.subTest(flag=flag):
                self.assertEqual(data_status({'caseId':'SYN-XREPO-001','isFictionalDemo':flag}),expected)
        self.assertEqual(data_status({'caseId':'SYN-XREPO-001'}),'pending-confirmation')
        with self.assertRaises(KeyError): data_status({})

    def test_import_boundary(self):
        build_gisis({'caseId':'SYN-XREPO-001','isFictionalDemo':True},[])
        self.assertNotIn('mcis_service.reports.service',sys.modules)
        self.assertNotIn('mcis_service.main',sys.modules)
        self.assertFalse(any('seed' in n for n in sys.modules if n.startswith('mcis_service.')))

if __name__ == '__main__': unittest.main(verbosity=2)
