"""Internal exact reads over existing media tables; no ORM/application imports.

The caller must authorize the case and own a consistent read transaction. Neither
this adapter nor a caller-provided reader authenticates an HTTP request.
"""
from copy import deepcopy
from hashlib import sha256
import json

from .media_reference import ProjectionUnavailable, project_saved_media


def _fail(code):
    raise ProjectionUnavailable(code)


class ScopedMediaReader:
    """Existing Session.scalars(select(Model).where(...)).all() query shape.

    Inject existing audio Revision/image Record classes and SQLAlchemy select
    from an already authorized call site; never import app.py to obtain them here.
    evidence_reader(case_id, evidence_id) must return a derived current item in
    the same read scope, not list all case evidence or check/open original bytes.
    No transaction, flush, write, source download, latest lookup or fallback here.
    """
    def __init__(self, *, case_id, session, select, audio_model, image_model, evidence_reader):
        if not isinstance(case_id, str) or not case_id:
            _fail('invalid_identity')
        self.case_id = case_id
        self._session = session
        self._select = select
        self._models = {'audio': audio_model, 'image': image_model}
        self._evidence_reader = evidence_reader

    def read_revision(self, media, run_id, revision):
        model = self._models[media]
        query = self._select(model).where(model.case_id == self.case_id,
                                         model.run_id == run_id,
                                         model.revision == revision)
        with self._session.no_autoflush:
            rows = self._session.scalars(query).all()
        return [{'case_id': r.case_id, 'run_id': r.run_id, 'revision': r.revision,
                 'doc': deepcopy(r.doc)} for r in rows]

    def read_evidence(self, evidence_id):
        return deepcopy(self._evidence_reader(self.case_id, evidence_id))


def _canonical(value):
    # Versioned Python JSON recipe; no Unicode normalization or float coercion.
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=True, allow_nan=False).encode('ascii')
    except (TypeError, ValueError):
        _fail('revision_content_unknown')


COMMON = ('expectedRevision', 'revision', 'text', 'reason', 'operator', 'role', 'utc', 'factVerified')
IMAGE = ('lineIndex', 'decision')
AUDIO = ('segmentId', 'hearingStatus', 'startMs', 'endMs', 'timeStatus', 'speaker',
         'machineArtifactSha256', 'audioSha256')


def _one(reader, media, case_id, run_id, revision):
    rows = reader.read_revision(media, run_id, revision)
    if not isinstance(rows, list):
        _fail('saved_shape_unknown')
    if not rows:
        _fail('initial_missing' if revision == 0 else 'revision_missing')
    if len(rows) != 1:
        _fail('ambiguous_revision')
    row = rows[0]
    if row['case_id'] != case_id:
        _fail('case_mismatch')
    if row['run_id'] != run_id:
        _fail('run_mismatch')
    if type(row['revision']) is not int or row['revision'] != revision:
        _fail('revision_mismatch')
    return deepcopy(row)


def read_exact_media_reference(*, reader, media, case_id, run_id, revision,
                               evidence_id, evidence_role, expected_reference_sha256=None):
    """reader may instead be a trusted case-scoped read-only implementation.

    Read only revision zero, the exact human revision and required source items.
    Missing exact row is revision_missing: do not scan history to distinguish
    absence of all human history. No writes and no automatic retry.
    """
    if reader.case_id != case_id:
        _fail('case_mismatch')
    if media not in ('audio', 'image') or evidence_role not in ({'audio'} if media == 'audio' else {'pdf', 'image'}):
        _fail('unsupported_media_role')
    if type(revision) is not int or not 1 <= revision <= 1000:
        _fail('invalid_revision')
    if any(not isinstance(v, str) or not v or v != v.strip() for v in (case_id, run_id, evidence_id)):
        _fail('invalid_identity')
    if expected_reference_sha256 is not None and (not isinstance(expected_reference_sha256, str) or len(expected_reference_sha256) != 64 or any(c not in '0123456789abcdef' for c in expected_reference_sha256)):
        _fail('invalid_reference_digest')
    try:
        initial = _one(reader, media, case_id, run_id, 0)
        human = _one(reader, media, case_id, run_id, revision)
        doc = initial['doc']
        source_ids = ([doc['machineDraft']['source']['evidenceId']] if media == 'audio'
                      else [doc['sourceVersions'][r]['evidenceId'] for r in ('pdf', 'image')])
        if evidence_id != source_ids[0 if evidence_role in ('audio', 'pdf') else 1]:
            _fail('evidence_mismatch')
        if any(not isinstance(e, str) or not e or e != e.strip() for e in source_ids):
            _fail('invalid_identity')
        items = []
        for eid in dict.fromkeys(source_ids):
            item = reader.read_evidence(eid)
            if item is None:
                _fail('evidence_missing_or_ambiguous')
            if item['caseId'] != case_id:
                _fail('case_mismatch')
            if item['evidenceId'] != eid:
                _fail('evidence_mismatch')
            items.append(item)
        projected = project_saved_media(media=media, case_id=case_id, run_id=run_id,
            revision=revision, evidence_id=evidence_id, evidence_role=evidence_role,
            saved_rows=[initial, human], evidence_items=items)
        fields = COMMON + (AUDIO if media == 'audio' else IMAGE)
        if set(human['doc']) != set(fields):
            _fail('revision_content_unknown')
        payload = {key: human['doc'][key] for key in fields}
        body = {'contract': 'saved-human-revision-digest/1', 'media': media,
                'caseId': case_id, 'runId': run_id, 'revision': revision, 'content': payload}
        projected['humanRevisionSha256'] = sha256(_canonical(body)).hexdigest()
        reference = {'contract': 'exact-media-report-reference/1', 'projection': projected}
        digest = sha256(_canonical(reference)).hexdigest()
        if expected_reference_sha256 is not None and digest != expected_reference_sha256:
            _fail('reference_content_changed')
        return {'contract': reference['contract'], 'referenceSha256': digest, 'projection': projected}
    except (KeyError, TypeError, IndexError, AttributeError):
        _fail('saved_shape_unknown')
