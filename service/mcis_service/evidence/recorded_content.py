"""Verify delivery bytes against trusted local records, not source authenticity."""
import re
from ..common.context import problem
from ..common.csjson import sha256_hex
from .service import custody_events
from .safe_content import read_content


def digest(value):
    if not isinstance(value, str) or re.fullmatch(r'[0-9a-fA-F]{64}', value) is None:
        raise problem(409, 'EVIDENCE_DIGEST_UNAVAILABLE', '记录摘要缺失或无效，未交付原件')
    return value.lower()


def read_recorded(s, case_id, item, path):
    expected = digest(item.get('sha256'))
    for event in custody_events(s, case_id, item['evidenceId']):
        if event.kind == 'Register' and digest(event.sha256) != digest(item.get('sha256')):
            raise problem(409, 'EVIDENCE_DIGEST_CONFLICT', '登记摘要冲突，未交付原件')
        if event.kind == 'Change':
            if digest(event.previous_sha256) != expected:
                raise problem(409, 'EVIDENCE_DIGEST_CONFLICT', '变更摘要衔接不一致，未交付原件')
            expected = digest(event.sha256)
    raw = read_content(path)
    if sha256_hex(raw) != expected:
        raise problem(409, 'EVIDENCE_CONTENT_MISMATCH', '内容与记录摘要不一致，未交付原件')
    return raw, expected
