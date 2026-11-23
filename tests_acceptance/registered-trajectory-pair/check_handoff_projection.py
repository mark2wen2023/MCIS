"""Small rejection checks; synthetic dictionaries, no registration or query run."""
import importlib.util
from pathlib import Path
import unittest
from copy import deepcopy
spec=importlib.util.spec_from_file_location('handoff',Path(__file__).with_name('joined_t100_handoff.py'))
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
def frame():
    return {'caseId':h.CASE,'alignedUtc':h.UTC,'vessels':[
        {'vesselId':v,'status':'input_point','locator':{'jsonPointer':pointer},'courseUsedAsHeading':False,
         'original':{'caseId':h.CASE,'evidenceId':'SYN-'+v,'requestDigest':d*64,'sourceSha256':s*64},
         'headingDeg':heading}
        for v,pointer,d,s,heading in [('SYN-VESSEL-A','/points/7','a','b',{'value':None,'kind':'missing'}),
         ('SYN-VESSEL-B','/points/12','c','d',{'value':270,'kind':'recorded'})]]}
class Check(unittest.TestCase):
    def test_minimum_and_no_mutation(self):
        f=frame();before=deepcopy(f);out=h.projection(f)
        self.assertEqual(f,before);self.assertEqual(len(out),2)
        self.assertEqual(set(out[0]),{'vesselId','evidenceId','requestDigest','sourceSha256','jsonPointer','observation'})
        self.assertIsNone(out[0]['observation']['value']);self.assertEqual(out[1]['observation']['value'],270)
    def test_wrong_context_and_missing_vessel(self):
        for key,value in [('caseId','SYN-OTHER'),('alignedUtc','2026-02-01T12:02:04.250Z'),('vessels',[])]:
            f=frame();f[key]=value
            with self.assertRaises(ValueError):h.projection(f)
    def test_wrong_locator_pin_or_heading(self):
        for key,value in [('locator',{'jsonPointer':'/points/8'}),('original',{}),('courseUsedAsHeading',True),
                          ('headingDeg',{'value':90,'kind':'recorded'})]:
            f=frame();f['vessels'][0][key]=value
            with self.assertRaises(ValueError):h.projection(f)
        for value in [None,float('nan'),True]:
            f=frame();f['vessels'][1]['headingDeg']['value']=value
            with self.assertRaises(ValueError):h.projection(f)
if __name__=='__main__':unittest.main(verbosity=2)
