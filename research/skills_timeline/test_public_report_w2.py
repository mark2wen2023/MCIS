"""Pinned public-report extraction replay, NOT original AIS/VDR validation."""
import csv
import hashlib
import json
from pathlib import Path
import unittest
from dataclasses import replace
from datetime import datetime

from preview import Rejected, preview
from test_real_w2 import DOTNET, DLL, RealTestCore
from test_preview import Repository

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class ReportProvenance(unittest.TestCase):
    def setUp(self):
        pin = json.loads((HERE / 'public_report_pin.json').read_text())
        for name, digest in pin['files'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest['sha256'])
        path = ROOT/'reports/yangze22/tracks_from_report.csv'
        with path.open() as f:
            rows = list(csv.DictReader(line for line in f if not line.startswith('#')))
        self.rows = [r for r in rows if r['vesselId']=='yangze22'
            and r['timeUtc']=='2024-12-30T14:01:54Z'
            and r['provenance'] in ('ReportFigure-AIS','ReportFigure-VDR')]
        self.assertEqual(len(self.rows), 2)

    def test_extraction_and_caption_traceability_not_image_verification(self):
        self.assertEqual({r['hdgDeg'] for r in self.rows}, {'47.0','48.0'})
        self.assertEqual({r['figure'] for r in self.rows}, {'图6','图27'})
        self.assertEqual({r['page'] for r in self.rows}, {'15','39'})
        report = ''.join((ROOT/'reports/yangze22/report.txt').read_text().split())
        for row in self.rows:
            self.assertIn(''.join(row['quote'].split()), report)
            self.assertEqual(datetime.fromisoformat(row['timeBeijing']),
                             datetime.fromisoformat(row['timeUtc']))
        # The captions exist. This does NOT verify the image pixel readings.

    def test_report_csv_is_not_silently_promoted_to_raw_nmea(self):
        repo = Repository()
        repo.records = {k: replace(v, format='report-derived-csv')
                        for k,v in repo.records.items()}
        class NeverCalled:
            def align(self, payload):
                raise AssertionError('Report format must not reach current NMEA preview')
        with self.assertRaises(Rejected):
            preview({'caseId':'CASE-1','sourceIds':['A','B'],
                'caseEpochUtc':'2024-12-30T14:01:54Z'},
                principal='fixture-investigator', repository=repo, core=NeverCalled())

    @unittest.skipUnless(DOTNET and DLL, 'real W2 requires explicit developer paths')
    def test_real_w2_csv_replay_only_heading_not_cog(self):
        # No fabricated NMEA and no interpolation. Same ship, same extracted UTC,
        # explicit HDG only. Caller selections are fixed test data, not a safe API.
        sources=[]
        for row in self.rows:
            sources.append({'sourceId':row['provenance'], 'format':'csv',
                'text':'time,heading\n'+row['timeUtc']+','+row['hdgDeg']+'\n',
                'emitGnssAnchors':False,
                'csvMapping':{'timeColumn':'time','timeZoneOffsetHours':0,
                    'columns':[{'column':'heading','kind':'Heading'}]}})
        core=RealTestCore()
        envelope=core.align({'caseId':'CJK-2024-1230-YangZe22-VegaDream',
            'caseEpochUtc':'2024-12-30T14:01:54Z','calibrate':False,'sources':sources})
        self.assertTrue(envelope['ok'])
        result=envelope['result']
        self.assertEqual(result['stats']['tracks'],2)
        self.assertEqual(result['conflicts'],[])  # 1 degree < default 2 degree threshold
        self.assertFalse(result['calibration']['allCalibrated'])
        # Zero conflicts is neither independent corroboration nor source accuracy.
