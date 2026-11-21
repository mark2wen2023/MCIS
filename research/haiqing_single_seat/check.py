"""Pinned ordinary imports from temporary Git bytes; no Pi/provider/service."""
from copy import deepcopy
from hashlib import sha1, sha256
import importlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SOURCES = {
    'packet.py': ('420284ab5fd44c94b737f8c1cf51bc0ef09aea29', 'research/expert_group/packet.py', 'ff2018dad2d58e9fe158f503ecd71a004c20e226'),
    'registered_query.py': ('0dc1226364524977a4155e480d96436443cd8967', 'service/mcis_service/trajectory_exchange/registered_query.py', 'a7a5a12294308395413af75de1837de284a94a1c'),
    'validation.py': ('0dc1226364524977a4155e480d96436443cd8967', 'service/mcis_service/trajectory_exchange/validation.py', 'cd1be59c2c74327ca5468eab06d1461c71ad0afe'),
    'vessel-a.json': ('2048c60fd6650c6f2c99a76a16be463a3895655d', 'tests_acceptance/shared-trajectory-cross-repo-expanded/vessel-a.json', 'd8e132c566f07004d76227af52745d5b5ad943c4'),
    'vessel-b.json': ('2048c60fd6650c6f2c99a76a16be463a3895655d', 'tests_acceptance/shared-trajectory-cross-repo-expanded/vessel-b.json', '7b332f3af0acbe9d5260fca88b889de95c5279c0'),
}


def materialize(folder):
    for name, (ref, path, expected) in SOURCES.items():
        entry = subprocess.check_output(['git', 'ls-tree', ref, '--', path], cwd=REPO, text=True).split()
        if entry != ['100644', 'blob', expected, path]:
            raise RuntimeError('Pinned ordinary Git entry differs: ' + name)
        raw = subprocess.check_output(['git', 'show', ref + ':' + path], cwd=REPO)
        if sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest() != expected:
            raise RuntimeError('Pinned Git bytes differ: ' + name)
        with (folder / name).open('xb') as stream:
            stream.write(raw)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class Checks(unittest.TestCase):
    def setUp(self):
        self.pins, self.entries = [], []
        # Independent identity expectations: not derived from frame or model args.
        for side, vid, eid in [('a', 'SYN-VESSEL-A', 'SYN-E-A'), ('b', 'SYN-VESSEL-B', 'SYN-E-B')]:
            raw = (INPUTS / f'vessel-{side}.json').read_bytes()
            document = json.loads(raw)
            self.assertEqual(document['caseId'], 'SYN-XREPO-001')
            self.assertEqual(document['vessel']['vesselId'], vid)
            pin = {'caseId': 'SYN-XREPO-001', 'evidenceId': eid,
                   'requestDigest': sha256(f'synthetic-receipt-{side}'.encode()).hexdigest(),
                   'sourceSha256': sha256(raw).hexdigest()}
            self.pins.append(pin)
            self.entries.append({'pin': pin, 'document': document})
        self.frame = {'caseId': seat.CASE, 'alignedUtc': seat.UTC, 'vessels': [
            project._point_from_committed_original(e, project._stamp(seat.UTC)) for e in self.entries]}

    def prepare(self, frame=None):
        return seat.prepare(self.frame if frame is None else frame, trusted_pins=self.pins)

    def handoff(self, args):
        return seat.handoff(host._validate, args, frame=self.frame, trusted_pins=self.pins)

    def review(self, packet):
        return {'reviews': [{'itemId': item['itemId'], 'label': 'insufficient', 'quote': item['sourceText'],
                'rationale': seat.CLAIM, 'uncertainty': seat.LIMIT} for item in packet['items']]}

    def test_one_note_with_gap_and_explicit_absence(self):
        packet, _ = self.prepare()
        self.assertNotIn('jsonPointer', json.dumps(packet)); self.assertNotIn('sourceSha256', json.dumps(packet))
        note = self.handoff(self.review(packet))
        self.assertEqual(note['references']['item_001'], {'original': self.pins[0], 'locator': {'jsonPointer': seat.GAP_POINTER}})
        gap = self.entries[0]['document']['sampling']['missingIntervals'][1]
        self.assertLess(project._stamp(gap['startUtc']), project._stamp(note['alignedUtc']))
        self.assertLess(project._stamp(note['alignedUtc']), project._stamp(gap['endUtc']))
        self.assertIsNone(note['references']['item_002'])
        self.assertIn('no exact observation', note['items'][1]['quote'])
        self.assertIn('insufficient', note['text'])
        self.assertEqual(note['status'], 'proposed_note_pending_human_review')
        self.assertFalse(note['factActivated']); self.assertFalse(note['saved'])

    def test_wrong_case_wrong_time_and_borrowed_pin(self):
        for key, value in [('caseId', 'SYN-OTHER'), ('alignedUtc', '2026-02-01T12:02:05.000Z')]:
            with self.subTest(key=key), self.assertRaises(seat.ScopeError): self.prepare({**self.frame, key: value})
        for mutate in ('pin', 'identity', 'order'):
            bad = deepcopy(self.frame)
            if mutate == 'pin': bad['vessels'][0]['original'] = self.pins[1]
            elif mutate == 'identity': bad['vessels'][0]['vesselId'] = 'MODEL-CHOSEN'
            else: bad['vessels'].reverse()
            with self.subTest(mutate=mutate), self.assertRaises(seat.ScopeError): self.prepare(bad)

    def test_absence_cannot_borrow_neighbor_or_other_vessel(self):
        neighboring = project._point_from_committed_original(self.entries[1], project._stamp('2026-02-01T12:02:05.000Z'))['locator']
        self.assertTrue(neighboring['jsonPointer'].startswith('/points/'))
        for locator in (neighboring, {'jsonPointer': seat.GAP_POINTER}):
            bad = deepcopy(self.frame); bad['vessels'][1]['locator'] = locator
            with self.subTest(locator=locator), self.assertRaises(seat.ScopeError): self.prepare(bad)
        bad = deepcopy(self.frame); bad['vessels'][0]['locator'] = {'jsonPointer': '/sampling/missingIntervals/0'}
        with self.assertRaises(seat.ScopeError): self.prepare(bad)

    def test_real_validator_rejects_borrowed_quote_or_scope_fields(self):
        packet, _ = self.prepare()
        for patch in ({'quote': packet['items'][0]['sourceText']}, {'itemId': 'neighbor'}, {'locator': {'jsonPointer': '/points/3'}}):
            proposal = self.review(packet); proposal['reviews'][1].update(patch)
            with self.subTest(patch=patch), self.assertRaises(host.GroupError): self.handoff(proposal)
        for field, value in [('frame', self.frame), ('trusted_pins', self.pins)]:
            proposal = self.review(packet); proposal[field] = value
            with self.subTest(field=field), self.assertRaises(host.GroupError): self.handoff(proposal)

    def test_no_definitive_claim_even_if_host_shape_accepts(self):
        packet, _ = self.prepare()
        for patch in ({'label': 'supported'}, {'rationale': 'Vessel B did not turn.'}):
            proposal = self.review(packet); proposal['reviews'][1].update(patch)
            host._validate(proposal, packet)
            with self.subTest(patch=patch), self.assertRaises(seat.ScopeError): self.handoff(proposal)


if __name__ == '__main__':
    if not sys.flags.isolated: raise SystemExit('Use an existing Python with -I; no install/fetch.')
    sys.dont_write_bytecode = True
    with tempfile.TemporaryDirectory(prefix='mcis-seat-source-') as folder:
        INPUTS = Path(folder) / 'service' / 'mcis_service' / 'trajectory_exchange'
        INPUTS.mkdir(parents=True)
        materialize(INPUTS)  # All five verified before any import; missing objects fail, no fetch.
        package = ModuleType('_frozen_trajectory'); package.__path__ = [str(INPUTS)]
        sys.modules[package.__name__] = package
        project = importlib.import_module('_frozen_trajectory.registered_query')
        validation = sys.modules['_frozen_trajectory.validation']
        if Path(project.__file__).resolve() != (INPUTS / 'registered_query.py').resolve() or Path(validation.__file__).resolve() != (INPUTS / 'validation.py').resolve():
            raise RuntimeError('Unexpected module source')
        host = module('_frozen_review', INPUTS / 'packet.py')
        seat = module('_offline_seat', ROOT / 'seat_note.py')
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
        if any(n == 'mcis_service' or n.startswith('mcis_service.') for n in sys.modules):
            raise RuntimeError('Application package unexpectedly imported')
    raise SystemExit(0 if result.wasSuccessful() else 1)
