"""Opt-in real W2 integration with synthetic evidence, NOT production auth/LLM.
Run: MCIS_TEST_DOTNET=/absolute/dotnet MCIS_TEST_CORE_DLL=/absolute/mcis-core.dll
     python -m unittest -v test_real_w2
Executable paths are developer configuration, never user request fields.
"""
import json
import os
from pathlib import Path
import subprocess
import unittest
from dataclasses import replace
from hashlib import sha256

from preview import Source, preview, Rejected
from test_preview import Repository

DOTNET = os.environ.get('MCIS_TEST_DOTNET')
DLL = os.environ.get('MCIS_TEST_CORE_DLL')


def fixture(heading, times=(0, 1, 2), checksum_valid=True):
    """Fictional checksum-correct NMEA; no real vessel/investigation evidence."""
    body = f'HEHDT,{heading:.1f},T'
    checksum = 0
    for char in body:
        checksum ^= ord(char)
    if not checksum_valid:
        checksum ^= 1
    return '\n'.join(f'2026-11-13T00:00:{t:02d}Z ${body}*{checksum:02X}' for t in times)


class RealTestCore:
    """Test-only fixed-fixture runner, NOT a production bounded transport."""
    def __init__(self):
        self.calls = 0
        self.last = None

    def align(self, payload):
        self.calls += 1
        process = subprocess.run(
            [str(Path(DOTNET).resolve()), str(Path(DLL).resolve()), 'align'],
            input=json.dumps(payload), text=True, capture_output=True, timeout=10,
            env={'DOTNET_CLI_TELEMETRY_OPTOUT': '1', 'DOTNET_NOLOGO': '1'})
        self.last = json.loads(process.stdout)
        if process.returncode not in (0, 4):
            raise AssertionError(f'W2 unexpected exit {process.returncode}')
        return self.last


@unittest.skipUnless(DOTNET and DLL, 'requires built real W2 and explicit developer paths')
class RealW2Tests(unittest.TestCase):
    def setUp(self):
        self.repo = Repository()
        self.core = RealTestCore()
        self.request = {'caseId':'CASE-1', 'sourceIds':['A','B'],
                        'caseEpochUtc':'2026-11-13T00:00:00Z'}
        self.source('A', fixture(90))
        self.source('B', fixture(110))

    def source(self, sid, text):
        self.repo.records[sid] = Source('CASE-1', sid, 'real-test-r1',
            sha256(text.encode()).hexdigest(), f'fictional:{sid}', text)

    def run_preview(self):
        return preview(self.request, principal='fixture-investigator',
                       repository=self.repo, core=self.core)

    def test_real_conflict_binds_exact_sources_and_remains_uncalibrated(self):
        result = self.run_preview()
        self.assertEqual(len(result['candidates']), 1)
        candidate = result['candidates'][0]
        self.assertEqual(candidate['a']['sourceId'], 'A')
        self.assertEqual(candidate['b']['sourceId'], 'B')
        self.assertEqual(candidate['a']['digest'], self.repo.records['A'].digest)
        self.assertEqual(result['coreVersion'], 'mcis-core/0.1.0')
        self.assertEqual(result['status'], 'needs_human_review')
        raw = self.core.last['result']
        self.assertEqual(raw['conflicts'][0]['delta'], 20)
        self.assertFalse(raw['calibration']['allCalibrated'])
        self.assertEqual(raw['stats']['sentencesUsed'], 6)

    def test_equal_values_zero_is_not_consistency_proof(self):
        self.source('B', fixture(90))
        result = self.run_preview()
        self.assertEqual(result['candidates'], [])
        self.assertEqual(result['importQuality']['state'], 'coverage_unverified')
        self.assertFalse(result['importQuality']['timeOverlapVerified'])

    def test_disjoint_times_no_coverage_claim(self):
        self.source('B', fixture(110, (30,31,32)))
        result = self.run_preview()
        self.assertEqual(result['candidates'], [])
        self.assertFalse(result['importQuality']['timeOverlapVerified'])

    def test_bad_checksum_source_is_insufficient_import(self):
        self.source('B', fixture(110, checksum_valid=False))
        result = self.run_preview()
        self.assertEqual(result['importQuality']['state'], 'insufficient_import')
        self.assertGreater(result['importQuality']['unverifiedDiagnosticCount'], 0)
        self.assertNotIn('importDiagnostics', result)

    def test_unparseable_sources_are_not_clean(self):
        self.source('A', 'not NMEA')
        self.source('B', 'not NMEA')
        result = self.run_preview()
        self.assertEqual(result['importQuality']['state'], 'insufficient_import')
        self.assertEqual(result['candidates'], [])

    def test_revocation_after_real_execution_releases_no_preview(self):
        calls = 0
        def recheck(*args):
            nonlocal calls
            calls += 1
            return calls == 1
        self.repo.recheck = recheck
        with self.assertRaises(Rejected):
            self.run_preview()
        self.assertEqual(self.core.calls, 1)
