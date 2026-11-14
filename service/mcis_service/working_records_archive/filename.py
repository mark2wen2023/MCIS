"""Recover only a revalidated historical intake basename; never a server path."""
from urllib.parse import quote
from fastapi import HTTPException
from ..evidence_intake.parser import preview, canonical
from .validation import fail


def disposition(history, raw, case_id, evidence_id):
    try:
        meta = history.doc['metadata']
        binding = meta['binding']
        body = {**binding['metadata'], 'profile': binding['profile'], 'fileName': binding['fileName']}
        result, rebuilt = preview(body, raw, case_id, binding['operator'], binding['role'])
        if (binding['role'] not in ('Investigator', 'LeadInvestigator')
                or canonical(rebuilt) != canonical(binding)
                or result['requestDigest'] != history.key
                or meta['requestDigest'] != history.key
                or meta['evidenceId'] != evidence_id
                or result['sourceSha256'] != meta['sourceSha256']):
            raise ValueError()
        return 'attachment; filename="historical-source.bin"; filename*=UTF-8\'\'' + quote(result['fileName'], safe='')
    except (KeyError, TypeError, ValueError, UnicodeError, HTTPException):
        fail('历史附件文件名或登记绑定不一致', 'ARCHIVE_HISTORY_INTEGRITY', 409)
