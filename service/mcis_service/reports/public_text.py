"""Bounded, hash-pinned excerpts from an explicitly authorized public report.

No conclusions are computed here. New/changed source files require explicit review
and a new pinned digest; missing or modified files yield no excerpt.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from ..config import PROJECT_ROOT

CASE_ID = 'CJK-2024-1230-YangZe22-VegaDream'
SOURCE_PATH = 'reports/yangze22/report.txt'
SOURCE_SHA256 = 'bca8f8b8ba04a5d0669a121bc6c9380c8cd6f8397f67be2d0b30b38871c22ef2'
EVIDENCE_ID = 'EV-201'
MAX_LINES = 18
MAX_CHARS = 800


def excerpts(case: dict, template: dict, root: Path = PROJECT_ROOT) -> dict[str, dict]:
    if (case.get('caseId') != CASE_ID or case.get('isFictionalDemo') is not False
            or template.get('templateId') != 'cn-msa'):
        return {}
    try:
        raw = (root / SOURCE_PATH).read_bytes()
        if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
            return {}
        text = raw.decode('utf-8')
    except (OSError, UnicodeError):
        return {}
    # split('\n'), not splitlines(): form feeds belong to their physical line.
    lines = text.split('\n')
    titles = {s['titleZh']: s['sectionId'] for s in template['sections']}
    starts = [(i, titles[line.strip()]) for i, line in enumerate(lines) if line.strip() in titles]
    result = {}
    for index, (start, section_id) in enumerate(starts):
        stop = starts[index + 1][0] if index + 1 < len(starts) else len(lines)
        first = start + 1
        while first < stop and not lines[first].strip():
            first += 1
        end = first
        while end < min(stop, first + MAX_LINES):
            if len('\n'.join(lines[first:end + 1])) > MAX_CHARS:
                break
            end += 1
        while end > first and not lines[end - 1].strip():
            end -= 1
        quote = '\n'.join(lines[first:end])
        if not quote.strip():
            continue
        page_start = 1 + '\n'.join(lines[:first + 1]).count('\f')
        page_end = 1 + '\n'.join(lines[:end]).count('\f')
        result[section_id] = {
            'quote': quote, 'lineStart': first + 1, 'lineEnd': end,
            'pdfPageStart': page_start, 'pdfPageEnd': page_end,
            'sourceRef': (f'{SOURCE_PATH}#L{first + 1}-L{end}; SHA256={SOURCE_SHA256}; '
                          f'PDF页={page_start}–{page_end}; 正文页={page_start - 2}–{page_end - 2}'),
        }
    return result


def display_quote(value: str) -> str:
    """Normalize page breaks and XML-forbidden controls for PDF/DOCX rendering.

    The stored evidence, SHA256 and line reference always identify original bytes.
    """
    value = value.replace('\f', '\n')
    return ''.join(c for c in value if c in '\t\n\r' or 0x20 <= ord(c) <= 0xD7FF
                   or 0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF)
