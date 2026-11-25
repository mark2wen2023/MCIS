"""Pure preflight for a trusted case-service caller; not an authentication layer.

The case service must load the evidence and custody state under its existing
access checks, verify the whole custody chain, and read the exact authorized
bytes. Never construct this snapshot from LLM output or an HTTP request body.
No files, DB writes, routes, or model execution occur here.
"""
from hashlib import sha256
import re


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def _digest(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def preflight_case_drawing(*, case_id, evidence_id, evidence_state, source_bytes,
                           parsed_document, custody_chain_verified):
    """Match a trusted evidence snapshot to exact source bytes and parser identity.

    This profile only handles a directly parsed original; DWG-derived DXF needs
    a separately verified derivative lineage. It returns an audit-safe receipt,
    not a permission token or a claim that parsed entities are genuine.
    """
    if not _nonempty(case_id) or not _nonempty(evidence_id):
        raise ValueError('invalid case or evidence identifier')
    if not isinstance(evidence_state, dict) or evidence_state.get('caseId') != case_id or evidence_state.get('evidenceId') != evidence_id:
        raise ValueError('case evidence scope mismatch')
    if custody_chain_verified is not True:
        raise ValueError('verified custody chain required')
    if evidence_state.get('needsReview') is not False or evidence_state.get('status') != 'Verified':
        raise ValueError('verified evidence without pending review required')
    expected = evidence_state.get('currentSha256')
    if not _digest(expected) or not isinstance(source_bytes, bytes) or not source_bytes:
        raise ValueError('valid evidence hash and nonempty source bytes required')
    actual = sha256(source_bytes).hexdigest()
    if actual != expected:
        raise ValueError('source bytes differ from current evidence hash')
    if not isinstance(parsed_document, dict) or parsed_document.get('format') != 'dxf' or parsed_document.get('status') not in ('parsed','partial'):
        raise ValueError('direct DXF parse required; derivative lineage not supported')
    if parsed_document.get('sha256') != actual or parsed_document.get('id') != actual:
        raise ValueError('parsed drawing identity differs from verified source')
    return dict(case_id=case_id, evidence_id=evidence_id, drawing_sha256=actual,
                custody_chain_verified=True, source_bytes_match=True,
                parsed_identity_match=True, parsed_entities_authenticated=False,
                role_authenticated=False, execution_authorized=False,
                research_only=True, lofting_authorized=False)
