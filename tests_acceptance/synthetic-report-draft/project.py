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
    return _project(report, proposal, rubric=rubric, page_mode=True)


def _project(report, proposal, *, rubric, page_mode):
    location = ('page', 'paragraph') if page_mode else ('paragraph',)
    span_fields = (*location, 'start', 'length', 'quote')
    h.exact(report, 'reportId paragraphs')
    h.ident(report['reportId'])
    paragraphs = {}
    for p in h.array(report['paragraphs'], 1, 20):
        h.exact(p, ' '.join((*location, 'text')))
        for field in location:
            h.integer(p[field], 1, 100)
        h.text(p['text'], 4000)
        key = tuple(p[k] for k in location)
        if key in paragraphs:
            raise ValueError('duplicate paragraph')
        paragraphs[key] = p['text']
    h.exact(rubric, 'sourceDigest annotations')
    if rubric['sourceDigest'] != digest(report):
        raise ValueError('host source changed')
    annotations = {}
    for a in h.array(rubric['annotations'], 1, 20):
        h.exact(a, ' '.join((*span_fields, 'kind', 'sourceMode', 'timeWindow', 'conflictGroup')))
        h.integer(a['start'], 0, 4000); h.integer(a['length'], 1, 4000)
        key = tuple(a[k] for k in (*location, 'start', 'length'))
        if key in annotations or a['kind'] not in ('Event', 'Condition') or a['sourceMode'] not in ('reported', 'command'):
            raise ValueError('host annotation')
        text = paragraphs.get(key[:len(location)])
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
        h.exact(item, ' '.join(span_fields))
        for field in (*location, 'start', 'length'):
            h.integer(item[field], 0 if field == 'start' else 1, 4000)
        h.text(item['quote'], 4000)
        key = tuple(item[k] for k in (*location, 'start', 'length'))
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


def project_utf8(raw, proposal, *, host, rubric):
    """Test-host-only single source; host/rubric are NOT authenticated identities.

    Only proposal is simulated extractor output. No page mode or business adapter.
    """
    h.exact(host, 'caseId sourceId rawSha256')
    h.ident(host['caseId']); h.ident(host['sourceId']); h.sha(host['rawSha256'])
    h.exact(rubric, 'binding annotations')
    h.exact(rubric['binding'], 'caseId sourceId rawSha256')
    if rubric['binding'] != host:
        raise ValueError('host binding changed')
    h.exact(proposal, 'items')
    annotations = h.array(rubric['annotations'], 1, 20)
    spec = importlib.util.spec_from_file_location(
        'utf8_locator', ROOT / 'tests_acceptance/synthetic-utf8-locator/check.py')
    locator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(locator)  # Guarded unittest main is not executed.
    span_fields = ('paragraph', 'start', 'length', 'quote')
    for a in annotations:
        h.exact(a, 'paragraph start length quote kind sourceMode timeWindow conflictGroup')
        locator.locate(raw, {k: a[k] for k in span_fields}, expected_sha256=host['rawSha256'])
    # Same LF rule as locate, after its strict raw digest/format validation.
    paragraphs = [{'paragraph': i, 'text': line} for i, line in enumerate(
        (line for line in raw.decode('utf-8').split('\n') if line.strip()), 1)]
    report = {'reportId': host['sourceId'], 'paragraphs': paragraphs}
    projection_digest = digest(report)  # Not the raw byte SHA; never interchangeable.
    locations = []
    for item in h.array(proposal['items'], 1, 20):
        locations.append(locator.locate(raw, item, expected_sha256=host['rawSha256']))
    result = _project(report, {'reportId': host['sourceId'], 'sourceDigest': projection_digest,
                              'items': proposal['items']},
                      rubric={'sourceDigest': projection_digest, 'annotations': annotations},
                      page_mode=False)
    for node, location in zip(result['nodes'], locations, strict=True):
        node['source'] = {**deepcopy(host), **location, 'projectionDigest': projection_digest}
    result['scope'] = deepcopy(host)
    result['mode'] = 'synthetic_utf8_logical_paragraphs'
    return result
