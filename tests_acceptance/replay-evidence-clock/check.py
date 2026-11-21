"""Only pinned synthetic JSON, standalone validator and new pure query."""
from copy import deepcopy
import json
from pathlib import Path
import runpy
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
Q=runpy.run_path(str(ROOT/'tools/replay_evidence_clock/query.py'))
P=runpy.run_path(str(ROOT/'tools/replay_evidence_clock/preview.py'))
class Checks(unittest.TestCase):
 def setUp(self):self.tracks,self.device=Q['load_inputs']()
 def at(self,s):return Q['query'](self.tracks,self.device,s)
 def test_both_gap_endpoints_are_observations_no_heading_fallback(self):
  for t in [60,100,121,127.5]:
   a=self.at(t)['vessels'][0]
   self.assertEqual(a['status'],'input_point');self.assertEqual(a['position']['kind'],'recorded')
   self.assertIsNone(a['headingDeg']['value']);self.assertEqual(a['courseDeg']['value'],90)
   self.assertFalse(a['courseUsedAsHeading']);self.assertIsNone(a['collisionAngle'])
 def test_gap_interiors_and_boundary_neighbours_never_bridge(self):
  for t in [60.001,80,99.999,121.001,124.25,127.499]:
   a=self.at(t)['vessels'][0];self.assertEqual(a['status'],'declared_gap');self.assertIsNone(a['position']);self.assertEqual(a['records'],[])
  self.assertEqual(self.at(80)['vessels'][1]['status'],'input_point')
 def test_raw_clock_corrections_traceability(self):
  f=self.at(100);b=f['vessels'][1];self.assertEqual(b['time']['correctionSeconds'],12)
  self.assertEqual(b['time']['sourceUtc'],'2026-02-01T12:01:28.000Z')
  self.assertEqual(b['time']['alignedUtc'],f['alignedUtc']);r=b['records'][0]
  self.assertEqual(r['gitRef'],Q['FIXTURE_REF']);self.assertEqual(r['rawRecord']['time'],b['time'])
  index=int(r['jsonPointer'].split('/')[-1]);self.assertEqual(r['rawRecord'],self.tracks[1]['document']['points'][index])
  e=f['events'][0];self.assertEqual(e['time']['correctionSeconds'],7);self.assertEqual(e['time']['sourceUtc'],'2026-02-01T12:01:33.000Z')
  self.assertEqual(e['time']['alignedUtc'],f['alignedUtc']);self.assertIsNone(e['position'])
  self.assertEqual(e['associatedTrack']['vesselId'],'SYN-VESSEL-A')
 def test_unresolved_device_is_excluded_without_poisoning_valid_ships(self):
  for t in [0,100,220]:
   f=self.at(t);u=f['excludedDevices'][0]
   self.assertEqual(u['status'],'time_unresolved_not_synchronized');self.assertIsNone(u['time']['alignedUtc'])
   self.assertTrue(all(v['status']=='input_point' for v in f['vessels']))
   self.assertNotIn('SYN-DEVICE-02',[e['record']['rawRecord']['recordId'] for e in f['events']])
 def test_no_unrequested_interpolation_and_existing_quality_retained(self):
  self.assertTrue(all(p['position'] is None for p in self.at(1)['vessels']))
  f=self.at(20)
  self.assertTrue(all(v['position']['kind']=='interpolated' for v in f['vessels']))
  self.assertEqual(f['vessels'][1]['time']['sourceUtc'],'2026-02-01T12:00:08.000Z')
  self.assertEqual(f['vessels'][1]['time']['alignedUtc'],'2026-02-01T12:00:20.000Z')
  self.assertEqual(f['vessels'][1]['time']['correctionSeconds'],12)
 def test_read_only_and_cross_case_refused(self):
  old=deepcopy((self.tracks,self.device));self.at(100);self.assertEqual(old,(self.tracks,self.device))
  self.tracks[1]['document']['caseId']='SYN-OTHER'
  with self.assertRaisesRegex(ValueError,'CASE_MISMATCH'):self.at(100)
 def test_bad_device_clock_and_query_refused(self):
  self.device['document']['records'][0]['time']['correctionSeconds']=8
  with self.assertRaisesRegex(ValueError,'CLOCK_ARITHMETIC'):self.at(100)
  for t in [-1,221,float('nan'),True]:
   with self.assertRaises(ValueError):self.at(t)
 def test_html_payload_matches_query_and_no_external_sources(self):
  with tempfile.TemporaryDirectory() as d:
   target=Path(d)/'panel.html';html=P['build'](target)
   self.assertIn("connect-src 'none'",html);self.assertNotIn('fetch(',html)
   self.assertNotIn('<script src',html);self.assertNotIn('https://',html)
   data=json.loads(html.split('<script id="data" type="application/json">')[1].split('</script>')[0])
   self.assertEqual(next(f for f in data['frames'] if f['relativeSeconds']==100),self.at(100))
   with self.assertRaises(FileExistsError):P['build'](target)
if __name__=='__main__':unittest.main()
