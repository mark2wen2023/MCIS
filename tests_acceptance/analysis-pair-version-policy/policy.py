"""Unconnected internal policy experiment, not an authorization or production DTO.

Trusted caller must supply an explicitly selected ordered pair and an immutable
receipt captured from actual calculation inputs. This module cannot establish
that trust, issue such receipts, read originals, or decide latest by order/time.
"""
from dataclasses import dataclass
import re


class InvalidBinding(ValueError):
    pass


@dataclass(frozen=True)
class Source:
    vessel_id: str
    case_id: str
    evidence_id: str
    request_digest: str
    source_sha256: str


@dataclass(frozen=True)
class Pair:
    sources: tuple[Source, Source]


@dataclass(frozen=True)
class GenerationReceipt:
    generation_id: str
    inputs: Pair


def _identity(value):
    if type(value) is not str or not value or len(value) > 200 or any(ord(c) < 32 for c in value):
        raise InvalidBinding('IDENTITY')


def _context(case_id, vessel_ids):
    _identity(case_id)
    if type(vessel_ids) is not tuple or len(vessel_ids) != 2:
        raise InvalidBinding('ORDERED_VESSELS')
    for vessel in vessel_ids:
        _identity(vessel)
    if vessel_ids[0] == vessel_ids[1]:
        raise InvalidBinding('DUPLICATE_VESSEL')


def _pair(pair, case_id, vessel_ids):
    if type(pair) is not Pair or type(pair.sources) is not tuple or len(pair.sources) != 2:
        raise InvalidBinding('TWO_SOURCES')
    for source, vessel_id in zip(pair.sources, vessel_ids):
        if type(source) is not Source:
            raise InvalidBinding('SOURCE_TYPE')
        for value in (source.case_id, source.vessel_id, source.evidence_id):
            _identity(value)
        if source.case_id != case_id or source.vessel_id != vessel_id:
            raise InvalidBinding('CASE_OR_ORDERED_VESSEL')
        for value in (source.request_digest, source.source_sha256):
            if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
                raise InvalidBinding('DIGEST')
    a, b = pair.sources
    if a.evidence_id == b.evidence_id or a.request_digest == b.request_digest:
        raise InvalidBinding('DUPLICATE_ORIGINAL')


def freeze_pair(case_id, vessel_ids, entries):
    """Copy only existing registered-query vesselId/original fields.

    Caller must verify source ownership/selection separately. Ordinary JSON or
    a frozen Python object is NOT trusted by virtue of passing this function.
    No positions, raw text, timestamps or seed metadata are accepted here.
    """
    _context(case_id, vessel_ids)
    if type(entries) not in (tuple, list) or len(entries) != 2:
        raise InvalidBinding('TWO_SOURCES')
    sources = []
    for entry in entries:
        if type(entry) is not dict or set(entry) != {'vesselId', 'original'}:
            raise InvalidBinding('SOURCE_FIELDS')
        pin = entry['original']
        if type(pin) is not dict or set(pin) != {'caseId', 'evidenceId', 'requestDigest', 'sourceSha256'}:
            raise InvalidBinding('PIN_FIELDS')
        sources.append(Source(entry['vesselId'], pin['caseId'], pin['evidenceId'],
                              pin['requestDigest'], pin['sourceSha256']))
    pair = Pair(tuple(sources))
    _pair(pair, case_id, vessel_ids)
    return pair


def compare_versions(case_id, vessel_ids, *, selected, receipt):
    """Return only current/historical/unknown; malformed inputs raise.

    'current' means exact pair equality ONLY, not accuracy, access, completeness,
    fresh computation or suitability at a requested instant. Receipt absence
    (including historical seed output) remains unknown regardless of seed SHA.
    Compare again at delivery against current trusted selection, not a captured
    old selection. No async/session/revocation integration exists here.
    """
    _context(case_id, vessel_ids)
    if selected is not None:
        _pair(selected, case_id, vessel_ids)
    if receipt is not None:
        if type(receipt) is not GenerationReceipt:
            raise InvalidBinding('RECEIPT_TYPE')
        _identity(receipt.generation_id)
        _pair(receipt.inputs, case_id, vessel_ids)
    if selected is None or receipt is None:
        return 'unknown'
    return 'current' if selected == receipt.inputs else 'historical'
