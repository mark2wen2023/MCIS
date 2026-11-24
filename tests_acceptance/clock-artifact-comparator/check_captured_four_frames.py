"""Pinned synthetic artifact regression, NOT browser execution/attestation."""
import argparse
from copy import deepcopy
from datetime import datetime
import importlib.util
import os
from pathlib import Path
import unittest

os.environ['GIT_NO_LAZY_FETCH'] = '1'
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('fixed_comparator', HERE / 'compare.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
CAPTURE_SHA = 'c56ee87fb35aac8cc356314b2be4684b43fe33cbf8a90df7a968b498dcac6ec6'
NULL_FIELDS = ('time', 'positionKind', 'headingKind', 'headingMissing')
EXPECTED_OMISSIONS = tuple(
    (index, vessel, field)
    for index, vessel in ((1, 'SYN-VESSEL-B'), (2, 'SYN-VESSEL-A'),
                          (2, 'SYN-VESSEL-B'), (3, 'SYN-VESSEL-B'))
    for field in NULL_FIELDS
)


def require(condition, code):
    if not condition:
        raise m.Mismatch(code)


def same(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            same(actual[k], v) for k, v in expected.items())
    return actual == expected


def load_capture(path):
    raw = path.read_bytes()
    require(len(raw) == 4377 and m.digest(raw) == CAPTURE_SHA, 'capture_bytes')
    lines = raw.splitlines()
    require(len(lines) == 4, 'line_count')
    return [m.parse(line) for line in lines]


def reconcile(frames, truth=None):
    if truth is None:
        truth = m.fixed_receipt()  # Exact Git object + original receipt SHA, no fetch.
    require(truth['caseId'] == 'SYN-XREPO-001', 'fixed_case')
    require(isinstance(frames, list) and len(frames) == 4, 'frame_count')
    epoch = datetime.fromisoformat('2026-02-01T12:00:00+00:00')
    matched, omitted = 0, []
    for index, (frame, expected) in enumerate(zip(frames, truth['frames'], strict=True)):
        require(frame.get('alignedUtc') == expected['utc'], 'exact_utc')
        seconds = (datetime.fromisoformat(expected['utc'].replace('Z', '+00:00')) - epoch).total_seconds()
        require(type(frame.get('offsetSecondsFromClockEpoch')) in (int, float)
                and frame['offsetSecondsFromClockEpoch'] == seconds, 'offset')
        for field in ('simTime3dStr', 'simTime2dStr'):
            require(frame.get(field) == f'{seconds:.3f}', 'exact_seconds')
        require(type(frame.get('cpaAvailable')) is bool, 'explicit_cpa')
        if any(v['status'] == 'declared_gap' for v in expected['vessels']):
            require(frame['cpaAvailable'] is False, 'gap_cpa')
        vessels = frame.get('vessels')
        require(isinstance(vessels, dict) and set(vessels) ==
                {v['vesselId'] for v in expected['vessels']}, 'vessel_set')
        for vessel in expected['vessels']:
            vid = vessel['vesselId']
            actual = vessels[vid]
            require(isinstance(actual, dict), 'vessel_object')
            for key, value in vessel.items():
                identity = (index, vid, key)
                if key not in actual:
                    require(identity in EXPECTED_OMISSIONS and value is None, 'missing_required')
                    omitted.append(identity)
                else:
                    require(same(actual[key], value), 'field_' + key)
                    matched += 1
    require(tuple(omitted) == EXPECTED_OMISSIONS, 'omission_set')
    require(matched == 48, 'shared_field_count')
    return {'sharedVesselFields': matched, 'omittedExplicitNullFields': omitted,
            'browserExecutionVerified': False, 'pausedVerified': False,
            'candidateProvenanceVerified': False}


class Checks(unittest.TestCase):
    def setUp(self):
        self.frames = load_capture(INPUT)

    def test_fixed_capture_matches(self):
        result = reconcile(self.frames)
        self.assertEqual(result['sharedVesselFields'], 48)
        self.assertEqual(len(result['omittedExplicitNullFields']), 16)
        self.assertFalse(result['browserExecutionVerified'])
        print(result)

    def test_millisecond_and_both_clocks(self):
        for key, value in (('alignedUtc', '2026-02-01T12:02:08.000Z'),
                           ('simTime3dStr', '128.000'), ('simTime2dStr', '128.000')):
            frames = deepcopy(self.frames)
            frames[3][key] = value
            with self.subTest(key=key), self.assertRaises(m.Mismatch):
                reconcile(frames)

    def test_no_borrowed_original_point(self):
        for index in (1, 2, 3):
            frames = deepcopy(self.frames)
            frames[index]['vessels']['SYN-VESSEL-B']['jsonPointer'] = '/points/12'
            with self.subTest(index=index), self.assertRaises(m.Mismatch):
                reconcile(frames)

    def test_gap_cpa_requires_false_not_zero(self):
        for value in (True, 0, None):
            frames = deepcopy(self.frames)
            frames[2]['cpaAvailable'] = value
            with self.subTest(value=value), self.assertRaises(m.Mismatch):
                reconcile(frames)

    def test_required_fields_cannot_disappear(self):
        for key in self.frames[0]['vessels']['SYN-VESSEL-A']:
            if key not in ('vesselId', 'status', 'jsonPointer', 'fileSha256', *NULL_FIELDS):
                continue
            frames = deepcopy(self.frames)
            del frames[0]['vessels']['SYN-VESSEL-A'][key]
            with self.subTest(key=key), self.assertRaises(m.Mismatch):
                reconcile(frames)
        frames = deepcopy(self.frames)
        del frames[2]['cpaAvailable']
        with self.assertRaises(m.Mismatch):
            reconcile(frames)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--jsonl', type=Path, required=True)
    args, remaining = parser.parse_known_args()
    INPUT = args.jsonl
    load_capture(INPUT)  # Reject changed external bytes before any test mutation.
    unittest.main(argv=[__file__, *remaining], verbosity=2)
