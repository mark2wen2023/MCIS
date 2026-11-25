"""Check trusted DWG -> DXF research lineage; never grant execution permission.

The caller must load evidence, custody and reviewed conversion records from
trusted case storage. Hash agreement does not establish geometric fidelity.
"""
from hashlib import sha256
import json
import re


def _text(v):
    return isinstance(v, str) and bool(v.strip())


def _digest(v):
    return isinstance(v, str) and re.fullmatch(r'[0-9a-f]{64}', v) is not None


def record_digest(record):
    return sha256(json.dumps(record, sort_keys=True, separators=(',', ':'),
                            ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def verify_derivative_lineage(*, case_id, evidence_id, evidence_state,
                              source_bytes, derivative_bytes, conversion,
                              lineage_review, parsed_document, custody_chain_verified):
    if not _text(case_id) or not _text(evidence_id):
        raise ValueError('invalid case or evidence identifier')
    if not isinstance(evidence_state, dict) or evidence_state.get('caseId') != case_id or evidence_state.get('evidenceId') != evidence_id:
        raise ValueError('case evidence scope mismatch')
    if custody_chain_verified is not True or evidence_state.get('status') != 'Verified' or evidence_state.get('needsReview') is not False:
        raise ValueError('verified custody and evidence without pending review required')
    if not isinstance(source_bytes, bytes) or not re.fullmatch(rb'AC10[0-9]{2}', source_bytes[:6]):
        raise ValueError('DWG header required')
    if not isinstance(derivative_bytes, bytes) or not derivative_bytes:
        raise ValueError('nonempty derivative bytes required')
    source_hash = sha256(source_bytes).hexdigest()
    derivative_hash = sha256(derivative_bytes).hexdigest()
    if not _digest(evidence_state.get('currentSha256')) or evidence_state['currentSha256'] != source_hash:
        raise ValueError('original bytes differ from current evidence hash')
    if not isinstance(conversion, dict) or conversion.get('case_id') != case_id or conversion.get('evidence_id') != evidence_id:
        raise ValueError('conversion scope mismatch')
    if conversion.get('source_format') != 'dwg' or conversion.get('derivative_format') != 'dxf':
        raise ValueError('unsupported conversion format')
    if conversion.get('source_sha256') != source_hash or conversion.get('derivative_sha256') != derivative_hash:
        raise ValueError('conversion record hash mismatch')
    if type(conversion.get('returncode')) is not int or conversion['returncode'] != 0:
        raise ValueError('successful conversion record required')
    if not all(_text(conversion.get(k)) for k in ('tool', 'tool_version')) or not all(_digest(conversion.get(k)) for k in ('executable_sha256', 'log_sha256')):
        raise ValueError('conversion provenance required')
    conversion_hash = record_digest(conversion)
    if not isinstance(lineage_review, dict) or lineage_review.get('review') != 'accepted' or lineage_review.get('conversion_sha256') != conversion_hash or lineage_review.get('case_id') != case_id or lineage_review.get('evidence_id') != evidence_id or not _text(lineage_review.get('review_reference')):
        raise ValueError('matching reviewed conversion record required')
    if not isinstance(parsed_document, dict) or parsed_document.get('format') != 'dxf' or parsed_document.get('status') not in ('parsed','partial') or parsed_document.get('id') != derivative_hash or parsed_document.get('sha256') != derivative_hash:
        raise ValueError('parsed derivative identity mismatch')
    return dict(case_id=case_id, evidence_id=evidence_id, source_sha256=source_hash,
                derivative_sha256=derivative_hash, conversion_sha256=conversion_hash,
                source_bytes_match=True, derivative_bytes_match=True,
                reviewed_record_match=True, parsed_identity_match=True,
                converter_executable_verified=False, conversion_log_verified=False,
                geometric_fidelity_verified=False, parsed_entities_authenticated=False,
                role_authenticated=False, execution_authorized=False,
                research_only=True, lofting_authorized=False)
