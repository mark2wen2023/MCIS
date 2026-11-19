"""Opt-in internal range read. No permissions, media retrieval or transaction creation."""
from copy import deepcopy

from .media_reference import ProjectionUnavailable
from .media_reference_reader import read_exact_media_reference


def _fail(code):
    raise ProjectionUnavailable(code)


class _ObservedRead:
    """Capture exact rows already consumed by the reference reader, no second read.

    This is NOT a snapshot/transaction implementation. The trusted upstream reader
    must supply one authorized consistent view for the entire call.
    """
    def __init__(self, reader):
        self.case_id = reader.case_id
        self.reader = reader
        self.rows = {}

    def read_revision(self, media, run_id, revision):
        rows = deepcopy(self.reader.read_revision(media, run_id, revision))
        self.rows[revision] = rows
        return rows

    def read_evidence(self, evidence_id):
        return self.reader.read_evidence(evidence_id)


def read_exact_audio_range(*, reader, case_id, evidence_id, run_id, revision,
                           segment_id, expected_reference_sha256):
    """Read a trusted report's exact reference and its declared file-relative range.

    Caller must establish the existing report+media authorization intersection,
    source/task checks and a consistent read transaction. Expected digest must be
    from the trusted saved reference, never an untrusted client assertion. The
    persisted initial PCM basis must retain provenance from audio_review.source.
    Neither digest equality nor this function proves those preconditions.
    """
    if (not isinstance(expected_reference_sha256, str)
            or len(expected_reference_sha256) != 64
            or any(c not in '0123456789abcdef' for c in expected_reference_sha256)):
        _fail('invalid_reference_digest')
    if not isinstance(segment_id, str) or not segment_id or segment_id != segment_id.strip():
        _fail('invalid_identity')
    observed = _ObservedRead(reader)
    reference = read_exact_media_reference(reader=observed, media='audio', case_id=case_id,
        evidence_id=evidence_id, evidence_role='audio', run_id=run_id, revision=revision,
        expected_reference_sha256=expected_reference_sha256)
    if reference['projection']['target'] != {'segmentId': segment_id}:
        _fail('segment_mismatch')
    try:
        initial = observed.rows[0][0]['doc']
        human = observed.rows[revision][0]['doc']
        audio = initial['audio']
        draft = initial['machineDraft']
        source = draft['source']
        rate, frames = audio['sampleRateHz'], audio['frames']
        # Same bounded PCM basis as audio_review.source; never use ceil(durationMs)
        # alone as the endpoint, and never synthesize a missing historical basis.
        if (audio['format'] != 'PCM_WAV' or type(audio['channels']) is not int
                or audio['channels'] not in (1, 2) or type(audio['sampleWidthBytes']) is not int
                or audio['sampleWidthBytes'] not in (1, 2, 3, 4)
                or type(rate) is not int or not 8000 <= rate <= 48000
                or type(frames) is not int or not rate <= frames <= rate * 60
                or type(source['durationMs']) is not int
                or source['durationMs'] != (frames * 1000 + rate - 1) // rate):
            _fail('sample_basis_unknown')
        if type(draft['version']) is not int:
            _fail('sample_basis_unknown')
        if draft['version'] == 3:
            if (type(source['frameCount']) is not int or source['frameCount'] != frames
                    or type(source['sampleRateHz']) is not int or source['sampleRateHz'] != rate):
                _fail('sample_basis_unknown')
        elif draft['version'] != 2 or frames * 1000 % rate:
            _fail('sample_basis_unknown')
        start, end = human['startMs'], human['endMs']
        if start is None and end is None and human['timeStatus'] == 'unknown':
            status = 'unknown'
        elif (human['timeStatus'] == 'operator_declared' and type(start) is int
              and type(end) is int and 0 <= start < end and end * rate <= frames * 1000):
            status = 'operator_declared'
        else:
            _fail('range_unknown')
    except (KeyError, TypeError, IndexError, AttributeError):
        _fail('range_shape_unknown')
    return {
        'contract': 'exact-audio-file-range/1', 'caseId': case_id,
        'evidenceId': evidence_id, 'runId': run_id, 'revision': revision,
        'segmentId': segment_id, 'referenceSha256': reference['referenceSha256'],
        'sourceSha256': reference['projection']['sourceVersions']['audio']['sha256'],
        'rangeStatus': status, 'startMs': start, 'endMs': end,
        'timeBasis': {'kind': 'file-relative-milliseconds', 'frames': frames, 'sampleRateHz': rate},
        'factVerified': False, 'mediaRetrieved': False,
    }
