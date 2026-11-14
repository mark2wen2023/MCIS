"""Independent synthetic historical-binding tests; no HTTP or browser simulation claim."""
import copy
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import unquote

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'service'))
from mcis_service.evidence_intake.parser import preview
from mcis_service.working_records_archive.filename import disposition


def record(name='附件😀 “原稿”.zip'):
    raw = b'synthetic opaque attachment'
    body = dict(profile='mcis-evidence-intake-v1', fileName=name, title='Synthetic title',
                source='Synthetic source', extractedBy='Synthetic recorder',
                extractedUtc='2026-01-01T00:00:00Z', category='Document',
                confidentiality='Restricted', note='Fixture only')
    result, binding = preview(body, raw, 'SYNTHETIC', 'Reviewer', 'Investigator')
    return SimpleNamespace(key=result['requestDigest'], doc={'metadata': {
        'binding': binding, 'requestDigest': result['requestDigest'],
        'evidenceId': 'EV-TEST', 'sourceSha256': result['sourceSha256']}}), raw


@pytest.mark.parametrize('name', ['附件😀 “原稿”.zip', '😀'*123+'.docx', 'x";evil=.pdf', "x'%_.pdf", 'foo%2Fbar.pdf'])
def test_exact_unicode_encoded_once(name):
    history, raw = record(name)
    before = copy.deepcopy(history.doc)
    result = disposition(history, raw, 'SYNTHETIC', 'EV-TEST')
    prefix = 'attachment; filename="historical-source.bin"; filename*=UTF-8\'\''
    assert result.startswith(prefix)
    assert unquote(result[len(prefix):], errors='strict') == name
    assert result.isascii() and '\n' not in result and '\r' not in result
    assert history.doc == before


@pytest.mark.parametrize('field,value', [('caseId', 'OTHER'), ('byteLength', 1), ('version', '2'), ('role', 'Public'), ('operator', 'Changed'), ('sourceSha256', '0'*64), ('fileName', '../bad.pdf'), ('fileName', '\ud800.pdf'), ('metadata', None), ('metadata', [])])
def test_tampered_binding_fails_closed(field, value):
    history, raw = record()
    history.doc['metadata']['binding'][field] = value
    with pytest.raises(HTTPException) as exc:
        disposition(history, raw, 'SYNTHETIC', 'EV-TEST')
    assert exc.value.status_code == 409
    assert 'ARCHIVE_HISTORY_INTEGRITY' in str(exc.value.detail)


@pytest.mark.parametrize('which', ['case', 'evidence', 'raw', 'request', 'extra'])
def test_cross_context_and_extra_binding(which):
    history, raw = record()
    case, evidence = 'SYNTHETIC', 'EV-TEST'
    if which == 'case': case = 'OTHER'
    if which == 'evidence': evidence = 'OTHER'
    if which == 'raw': raw += b'changed'
    if which == 'request': history.key = '0'*64
    if which == 'extra': history.doc['metadata']['binding']['extra'] = 'untrusted'
    with pytest.raises(HTTPException) as exc:
        disposition(history, raw, case, evidence)
    assert exc.value.status_code == 409
