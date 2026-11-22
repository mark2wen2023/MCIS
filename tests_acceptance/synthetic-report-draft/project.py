"""Offline candidate only: synthetic host rubric, not automatic report semantics."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / 'research/semantic_support/evaluate.py'
spec = importlib.util.spec_from_file_location('shape_helpers', HELPER)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)  # Standard library only; no corpus or service is loaded.


def digest(report):
    return hashlib.sha256(json.dumps(report, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def project(report, proposal, *, rubric):
    """Host supplies the synthetic rubric independently of the simulated extractor.

    Exact location is checked; rubric labels are NOT inferred or professionally verified.
    No production caller, authorization, PDF extraction, graph conversion or persistence.
    """
    h.exact(report, 'reportId paragraphs')
    h.ident(report['reportId'])
    paragraphs = {}
    for p in h.array(report['paragraphs'], 1, 20):
        h.exact(p, 'page paragraph text')
        h.integer(p['page'], 1, 100); h.integer(p['paragraph'], 1, 100)
        h.text(p['text'], 4000)
        key = (p['page'], p['paragraph'])
        if key in paragraphs:
            raise ValueError('duplicate paragraph')
        paragraphs[key] = p['text']
    h.exact(rubric, 'sourceDigest annotations')
    if rubric['sourceDigest'] != digest(report):
        raise ValueError('host source changed')
    annotations = {}
    for a in h.array(rubric['annotations'], 1, 20):
        h.exact(a, 'page paragraph start length quote kind sourceMode timeWindow conflictGroup')
        h.integer(a['start'], 0, 4000); h.integer(a['length'], 1, 4000)
        key = (a['page'], a['paragraph'], a['start'], a['length'])
        if key in annotations or a['kind'] not in ('Event', 'Condition') or a['sourceMode'] not in ('reported', 'command'):
            raise ValueError('host annotation')
        text = paragraphs.get(key[:2])
        h.text(a['quote'], 4000)
        if (text is None or len(a['quote']) != a['length']
                or a['start'] + a['length'] > len(text)
                or text[a['start']:a['start'] + a['length']] != a['quote']):
            raise ValueError('host location')
        if a['timeWindow'] is not None:
            h.exact(a['timeWindow'], 'start end basis')
            for field in ('start', 'end', 'basis'):
                h.text(a['timeWindow'][field], 100)
                if a['timeWindow'][field] not in a['quote']:
                    raise ValueError('host time not quoted')
        if a['conflictGroup'] is not None:
            h.ident(a['conflictGroup'])
        annotations[key] = a
    h.exact(proposal, 'reportId sourceDigest items')
    if proposal['reportId'] != report['reportId'] or proposal['sourceDigest'] != digest(report):
        raise ValueError('proposal source changed')
    nodes, seen = [], set()
    for item in h.array(proposal['items'], 1, 20):
        # Extractor cannot provide coordinates, edges, claim status or time/interpretation.
        h.exact(item, 'page paragraph start length quote')
        for field in ('page', 'paragraph', 'start', 'length'):
            h.integer(item[field], 0 if field == 'start' else 1, 4000)
        h.text(item['quote'], 4000)
        key = tuple(item[k] for k in ('page', 'paragraph', 'start', 'length'))
        a = annotations.get(key)
        if key in seen or a is None or item['quote'] != a['quote']:
            raise ValueError('unbound citation')
        seen.add(key)
        nodes.append({'id': f'draft-{len(nodes)+1}', 'kind': a['kind'],
                      'text': item['quote'], 'status': 'Draft', 'strength': 'ToBeVerified',
                      'isPresumptive': True, 'sourceMode': a['sourceMode'],
                      'timeWindow': deepcopy(a['timeWindow']), 'timeSeconds': None,
                      'conflictGroup': a['conflictGroup'],
                      'source': {'reportId': report['reportId'], 'sourceDigest': digest(report),
                                 **deepcopy(item), 'offsetUnit': 'unicode_code_points'}})
    groups = {}
    for key, annotation in annotations.items():
        group = annotation['conflictGroup']
        if group is not None:
            groups.setdefault(group, set()).add(key)
    unselected_groups = []
    for group, members in sorted(groups.items()):
        selected = members & seen
        if selected and selected != members:
            raise ValueError('incomplete conflict group: ' + group)
        if not selected:
            unselected_groups.append(group)
    return {'status': 'synthetic_candidate_pending_review', 'nodes': nodes, 'edges': [],
            'extractionCoverageGuaranteed': False,
            'unselectedConflictGroups': unselected_groups,
            'scenarioReady': False, 'saved': False, 'modelCalled': False,
            'semanticSupportVerified': False, 'authorityVerified': False,
            'labelOrigin': 'hand_authored_synthetic_host_rubric'}
