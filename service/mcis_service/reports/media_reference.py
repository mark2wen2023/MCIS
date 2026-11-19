"""Internal exact saved-media projection; no I/O, ORM imports or public API.

Call only with authorized, consistent storage snapshots (see contract). Structural
validation cannot authenticate dictionaries supplied by an untrusted client.
"""
from copy import deepcopy


class ProjectionUnavailable(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _fail(code):
    raise ProjectionUnavailable(code)


def _id(value):
    if not isinstance(value, str) or not value or value != value.strip():
        _fail('invalid_identity')
    return value


def _digest(value):
    if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        _fail('source_digest_unknown')
    return value


def project_saved_media(*, media, case_id, run_id, revision, evidence_id,
                        evidence_role, saved_rows, evidence_items):
    """Rows: {case_id, run_id, revision, doc} copied from persisted ORM rows.

    evidence_items are derive/list_items results, NOT bare registration rows.
    Requested revision is exact, positive human revision (1..1000), never latest.
    Raises ProjectionUnavailable; never returns a partial citation on failure.
    """
    try:
        return _project(media, case_id, run_id, revision, evidence_id,
                        evidence_role, saved_rows, evidence_items)
    except (KeyError, TypeError, IndexError, AttributeError):
        _fail('saved_shape_unknown')


def _project(media, case_id, run_id, revision, evidence_id, role, rows, items):
    for value in (case_id, run_id, evidence_id):
        _id(value)
    if media not in ('image', 'audio') or role not in ({'pdf', 'image'} if media == 'image' else {'audio'}):
        _fail('unsupported_media_role')
    if type(revision) is not int or not 1 <= revision <= 1000:
        _fail('invalid_revision')
    if not isinstance(rows, list) or not isinstance(items, list):
        _fail('saved_shape_unknown')
    versions = {}
    for row in rows:
        if row['case_id'] != case_id:
            _fail('case_mismatch')
        if row['run_id'] != run_id:
            _fail('run_mismatch')
        n = row['revision']
        if type(n) is not int or not 0 <= n <= 1000:
            _fail('invalid_revision')
        if n in versions:
            _fail('ambiguous_revision')
        versions[n] = row['doc']
    if 0 not in versions:
        _fail('initial_missing')
    if not any(n > 0 for n in versions):
        _fail('no_human_revision')
    if revision not in versions:
        _fail('revision_missing')
    initial, human = versions[0], versions[revision]
    if type(human['revision']) is not int or human['revision'] != revision or type(human['expectedRevision']) is not int or human['expectedRevision'] != revision - 1:
        _fail('revision_mismatch')
    if human['factVerified'] is not False or not isinstance(human['text'], str):
        _fail('saved_shape_unknown')

    sources = {}
    if media == 'audio':
        draft = initial['machineDraft']; src = draft['source']
        if src['caseId'] != case_id:
            _fail('case_mismatch')
        sources['audio'] = {'evidenceId': _id(src['evidenceId']), 'sha256': _digest(src['currentSha256'])}
        if _digest(human['audioSha256']) != sources['audio']['sha256'] or _digest(human['machineArtifactSha256']) != _digest(draft['artifactSha256']):
            _fail('saved_source_mismatch')
        segment_id = _id(human['segmentId'])
        segments = draft['transcript']['segments'] + draft['transcript']['unlocatedSegments']
        if sum(s['id'] == segment_id for s in segments) != 1:
            _fail('target_missing_or_ambiguous')
        if human['hearingStatus'] not in ('pending', 'transcription_checked', 'unintelligible'):
            _fail('saved_shape_unknown')
        if human['hearingStatus'] == 'unintelligible' and human['text']:
            _fail('saved_shape_unknown')
        target = {'segmentId': segment_id}
        digests = {'registeredSha256': _digest(src['registeredSha256']),
                   'stateDigest': _digest(src['stateDigest']),
                   'machineArtifactSha256': _digest(draft['artifactSha256']),
                   'draftBytesSha256': _digest(initial['draftBytesSha256'])}
        status = human['hearingStatus']
    else:
        candidate = initial['candidate']; src = candidate['source']
        for name in ('pdf', 'image'):
            binding = initial['sourceVersions'][name]
            sources[name] = {'evidenceId': _id(binding['evidenceId']), 'sha256': _digest(binding['sha256'])}
            if sources[name]['sha256'] != _digest(src[name + '_sha256']):
                _fail('saved_source_mismatch')
        if _digest(initial['sourceVersions']['raw']['sha256']) != _digest(src['raw_sha256']):
            _fail('saved_source_mismatch')
        index = human['lineIndex']
        if type(index) is not int or not 0 <= index < len(candidate['text_lines']):
            _fail('target_missing_or_ambiguous')
        if human['decision'] not in ('pending', 'transcription-checked', 'unreadable'):
            _fail('saved_shape_unknown')
        target = {'lineIndex': index}
        digests = {'rawSha256': _digest(src['raw_sha256']),
                   'candidateBytesSha256': _digest(initial['sourceVersions']['candidate']['sha256'])}
        status = human['decision']
    if sources[role]['evidenceId'] != evidence_id:
        _fail('evidence_mismatch')
    # Both image source roles are mandatory; no fallback to the other matching hash.
    for source in sources.values():
        matches = [item for item in items if item['evidenceId'] == source['evidenceId']]
        if any(item['caseId'] != case_id for item in matches):
            _fail('case_mismatch')
        if len(matches) != 1:
            _fail('evidence_missing_or_ambiguous')
        if _digest(matches[0]['currentSha256']) != source['sha256']:
            _fail('source_changed')
    return deepcopy({'contract': 'saved-media-reference-projection/1', 'caseId': case_id,
                     'evidenceId': evidence_id, 'evidenceRole': role, 'media': media,
                     'runId': run_id, 'revision': revision, 'target': target,
                     'sourceVersions': sources, 'artifactDigests': digests,
                     'humanText': human['text'], 'reviewState': status,
                     'factVerified': False, 'associationPersisted': False,
                     'validationScope': 'saved-declarations-and-observed-register-only'})
