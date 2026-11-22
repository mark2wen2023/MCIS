"""Synthetic host binding + actual test-side locator/projector, no production auth."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('draft_project', Path(__file__).with_name('project.py'))
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)
RAW = '合成甲称：10:00至10:05有雾。\n\n合成乙称：同段无雾，待核。\n停车命令时刻未知，执行未确认。\n'.encode()
PIN = 'aa07189b6b376ab36cf31480afa5236409c4003581839c4860f81082f781dbd9'
NEW = RAW + '新增说明。\n'.encode()
NEW_PIN = '0c6b3195ded0da79a19752c6556da3da95d9ff64dbb832f2a61b815dcf76a184'


def fixture():
    host = {'caseId': 'synthetic-case', 'sourceId': 'synthetic-report', 'rawSha256': PIN}
    annotations, items = [], []
    for index, line in enumerate((s for s in RAW.decode().split('\n') if s.strip()), 1):
        item = {'paragraph': index, 'start': 0, 'length': len(line), 'quote': line}
        items.append(item)
        annotations.append({**item, 'kind': 'Event' if index == 3 else 'Condition',
                            'sourceMode': 'command' if index == 3 else 'reported',
                            'timeWindow': {'start': '10:00', 'end': '10:05', 'basis': '至'} if index == 1 else None,
                            'conflictGroup': 'fog' if index < 3 else None})
    return host, {'binding': deepcopy(host), 'annotations': annotations}, {'items': items}


def run(bundle, raw=RAW):
    host, rubric, proposal = bundle
    return p.project_utf8(raw, proposal, host=host, rubric=rubric)


class Checks(unittest.TestCase):
    def test_source_bound_drafts_no_page(self):
        bundle = fixture(); before = deepcopy(bundle)
        result = run(bundle)
        self.assertEqual(bundle, before)
        self.assertEqual(result['scope'], bundle[0])
        self.assertEqual(len(result['nodes']), 3)
        for node in result['nodes']:
            src = node['source']
            self.assertEqual(src['sourceSha256'], PIN)
            self.assertEqual(src['rawSha256'], PIN)
            self.assertNotEqual(src['projectionDigest'], PIN)
            self.assertEqual(RAW[src['byteStart']:src['byteEndExclusive']].decode(), node['text'])
            self.assertNotIn('page', src)
            self.assertIsNone(node['timeSeconds'])
            self.assertEqual(node['status'], 'Draft'); self.assertTrue(node['isPresumptive'])
        self.assertEqual(result['nodes'][2]['sourceMode'], 'command')
        self.assertIsNone(result['nodes'][2]['timeWindow'])
        self.assertEqual(result['edges'], [])
        for key in ('saved', 'scenarioReady', 'authorityVerified', 'semanticSupportVerified', 'extractionCoverageGuaranteed'):
            self.assertFalse(result[key])

    def test_new_sha_with_old_annotations_rejected(self):
        bundle = fixture(); bundle[0]['rawSha256'] = NEW_PIN
        with self.assertRaisesRegex(ValueError, '^host binding changed$'): run(bundle, NEW)
        with self.assertRaisesRegex(ValueError, '^source_digest$'): run(fixture(), NEW)
        bundle[1]['binding'] = deepcopy(bundle[0])  # Explicit test-host rebind, not extractor authority.
        result = run(bundle, NEW)
        self.assertEqual(result['scope']['rawSha256'], NEW_PIN)
        self.assertFalse(result['extractionCoverageGuaranteed'])

    def test_same_quote_different_source_or_case_rejected(self):
        for key in ('caseId', 'sourceId'):
            bundle = fixture(); bundle[0][key] = 'other-synthetic'
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, '^host binding changed$'):
                run(bundle)  # Identical raw bytes and quotes cannot reuse the old host binding.

    def test_extractor_cannot_claim_identity_page_or_position(self):
        for key, value in (('page', 1), ('position', [0, 0]), ('sourceId', 'synthetic-report'), ('rawSha256', PIN)):
            bundle = fixture(); bundle[2]['items'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): run(bundle)
        bundle = fixture(); bundle[1]['annotations'][0]['page'] = 1
        with self.assertRaises(ValueError): run(bundle)
        bundle = fixture(); bundle[2]['caseId'] = 'synthetic-case'
        with self.assertRaises(ValueError): run(bundle)

    def test_conflict_one_side_rejected_whole_group_uncovered(self):
        for index in (0, 1):
            bundle = fixture(); del bundle[2]['items'][index]
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, '^incomplete conflict group: fog$'):
                run(bundle)
        bundle = fixture(); bundle[2]['items'] = bundle[2]['items'][2:]
        result = run(bundle)
        self.assertEqual(result['unselectedConflictGroups'], ['fog'])
        self.assertFalse(result['extractionCoverageGuaranteed'])

    def test_late_invalid_item_returns_no_partial_draft(self):
        bundle = fixture(); bundle[2]['items'][-1]['length'] += 1
        before = deepcopy(bundle); returned = None
        with self.assertRaises(ValueError): returned = run(bundle)
        self.assertIsNone(returned); self.assertEqual(bundle, before)
        bundle = fixture(); bundle[1]['annotations'][-1]['length'] += 1
        with self.assertRaises(ValueError): run(bundle)


if __name__ == '__main__': unittest.main(verbosity=2)
