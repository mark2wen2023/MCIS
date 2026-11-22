"""Two hand-authored reports + simulated extraction; no real report/model/DB."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('projection', Path(__file__).with_name('project.py'))
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)


def fixture(second=False):
    texts = (['合成记录：记录员称10:00至10:05听到停车命令；未记载执行情况。',
              '合成记录：能见度情况未记载。'] if not second else
             ['合成记录：甲称11:00至11:10有雾；未注明日期与时区。',
              '合成记录：乙称同一期间无雾；没有独立核实。',
              '合成记录：停车命令时刻未知，是否执行未知。'])
    report = {'reportId': 'synthetic-b' if second else 'synthetic-a',
              'paragraphs': [{'page': 1 + i // 2, 'paragraph': i % 2 + 1, 'text': t}
                             for i, t in enumerate(texts)]}
    annotations, items = [], []
    for i, source in enumerate(report['paragraphs']):
        item = {k: source[k] for k in ('page', 'paragraph')}
        item.update(start=0, length=len(source['text']), quote=source['text'])
        command = (not second and i == 0) or (second and i == 2)
        window = None
        if i == 0:
            window = {'start': '11:00' if second else '10:00',
                      'end': '11:10' if second else '10:05', 'basis': '至'}
        annotations.append({**item, 'kind': 'Event' if command else 'Condition',
                            'sourceMode': 'command' if command else 'reported',
                            'timeWindow': window,
                            'conflictGroup': 'fog-disagreement' if second and i < 2 else None})
        items.append(item)
    rubric = {'sourceDigest': p.digest(report), 'annotations': annotations}
    proposal = {'reportId': report['reportId'], 'sourceDigest': p.digest(report), 'items': items}
    return report, proposal, rubric


def run(bundle):
    report, proposal, rubric = bundle
    return p.project(report, proposal, rubric=rubric)


class Checks(unittest.TestCase):
    def test_two_reports_remain_drafts(self):
        for second in (False, True):
            result = run(fixture(second))
            self.assertEqual(len(result['nodes']), 3 if second else 2)
            self.assertEqual(result['edges'], [])
            self.assertFalse(result['scenarioReady']); self.assertFalse(result['saved'])
            for node in result['nodes']:
                self.assertTrue(node['isPresumptive'])
                self.assertEqual(node['status'], 'Draft')
                self.assertIsNone(node['timeSeconds'])
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))

    def test_command_not_observed_execution_and_unknown_time(self):
        a, b = run(fixture()), run(fixture(True))
        self.assertEqual(a['nodes'][0]['sourceMode'], 'command')
        self.assertIn('未记载执行情况', a['nodes'][0]['text'])
        self.assertIsNone(b['nodes'][2]['timeWindow'])
        self.assertEqual(b['nodes'][2]['sourceMode'], 'command')
        self.assertEqual(b['nodes'][0]['conflictGroup'], b['nodes'][1]['conflictGroup'])
        self.assertIsNone(b['nodes'][1]['timeWindow'])  # No borrowed time from paragraph 1.

    def test_partial_conflict_group_rejected(self):
        for omitted in (0, 1):
            bundle = fixture(True)
            del bundle[1]['items'][omitted]
            with self.subTest(omitted=omitted), self.assertRaisesRegex(
                    ValueError, '^incomplete conflict group: fog-disagreement$'):
                run(bundle)

    def test_whole_conflict_group_absent_is_not_coverage(self):
        bundle = fixture(True)
        bundle[1]['items'] = bundle[1]['items'][2:]
        result = run(bundle)
        self.assertEqual(len(result['nodes']), 1)
        self.assertEqual(result['nodes'][0]['sourceMode'], 'command')
        self.assertEqual(result['unselectedConflictGroups'], ['fog-disagreement'])
        self.assertFalse(result['extractionCoverageGuaranteed'])
        complete = run(fixture(True))
        self.assertEqual(complete['unselectedConflictGroups'], [])
        self.assertFalse(complete['extractionCoverageGuaranteed'])

    def test_invented_quote_and_displaced_locator(self):
        for field, value in [('quote', '船舶已经停车。'), ('page', 9), ('paragraph', 2), ('start', 1)]:
            bundle = fixture(); bundle[1]['items'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): run(bundle)

    def test_tail_span_exact_length_and_bounds(self):
        bundle = fixture()
        text = bundle[0]['paragraphs'][0]['text']
        quote = '未记载执行情况。'
        start = text.index(quote)
        annotation = bundle[2]['annotations'][0]
        annotation.update(start=start, length=len(quote), quote=quote, timeWindow=None)
        bundle[1]['items'][0] = {k: annotation[k] for k in
                                 ('page', 'paragraph', 'start', 'length', 'quote')}
        result = run(bundle)
        self.assertEqual(result['nodes'][0]['source']['start'], start)
        self.assertEqual(result['nodes'][0]['text'], quote)
        self.assertEqual(start + len(quote), len(text))
        bad = deepcopy(bundle)
        bad[2]['annotations'][0]['length'] += 1
        bad[1]['items'][0]['length'] += 1
        with self.assertRaisesRegex(ValueError, '^host location$'):
            run(bad)
        for invalid in ('', '   ', None, 12):
            bad = deepcopy(bundle)
            bad[2]['annotations'][0]['quote'] = invalid
            with self.subTest(quote=invalid), self.assertRaises(ValueError):
                run(bad)

    def test_no_coordinates_or_causal_assertion(self):
        for field, value in [('position', {'lat': 0, 'lon': 0}), ('trajectory', []),
                             ('timeSeconds', 0), ('kind', 'Observation'), ('edges', []),
                             ('sourceMode', 'observed'), ('status', 'Confirmed')]:
            bundle = fixture(); bundle[1]['items'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): run(bundle)

    def test_changed_source_and_duplicate(self):
        bundle = fixture(); bundle[0]['paragraphs'][0]['text'] += '新版本'
        with self.assertRaises(ValueError): run(bundle)
        bundle = fixture(); bundle[1]['items'].append(deepcopy(bundle[1]['items'][0]))
        with self.assertRaises(ValueError): run(bundle)
        bundle = fixture(); bundle[1]['reportId'] = 'other'
        with self.assertRaises(ValueError): run(bundle)

    def test_no_mutation_and_empty_rejected(self):
        bundle = fixture(True); before = deepcopy(bundle); run(bundle)
        self.assertEqual(bundle, before)
        bundle[1]['items'] = []
        with self.assertRaises(ValueError): run(bundle)


if __name__ == '__main__': unittest.main(verbosity=2)
