"""Test-only byte-pinned locator; no I/O, authorization, PDF or extraction."""
import hashlib
import re
import unittest


def locate(raw, citation, *, expected_sha256):
    # Host fixture supplies this keyword, never a field in extractor citation.
    if (type(raw) is not bytes or len(raw) > 65536
            or type(expected_sha256) is not str
            or re.fullmatch('[0-9a-f]{64}', expected_sha256) is None
            or hashlib.sha256(raw).hexdigest() != expected_sha256):
        raise ValueError('source_digest')
    try:
        text = raw.decode('utf-8', errors='strict')
    except UnicodeDecodeError:
        raise ValueError('utf8') from None
    # Deliberately narrow LF-only format: no implicit conversion/page inference.
    if any(c in text for c in ('\r', '\f', '\ufeff', '\x00', '\u2028', '\u2029')):
        raise ValueError('text_format')
    paragraphs, offset = [], 0
    for line in text.split('\n'):
        if line.strip():
            paragraphs.append((offset, line))
        offset += len(line) + 1
    if not paragraphs:
        raise ValueError('empty_source')
    if type(citation) is not dict or set(citation) != {'paragraph', 'start', 'length', 'quote'}:
        raise ValueError('citation_fields')
    number, start, length, quote = (citation[k] for k in ('paragraph', 'start', 'length', 'quote'))
    if (any(type(n) is not int for n in (number, start, length))
            or not 1 <= number <= len(paragraphs) or start < 0 or length <= 0
            or type(quote) is not str or not quote.strip() or len(quote) != length):
        raise ValueError('span')
    base, paragraph = paragraphs[number - 1]
    end = start + length
    if end > len(paragraph) or paragraph[start:end] != quote:
        raise ValueError('quote_location')
    absolute_start, absolute_end = base + start, base + end
    byte_start = len(text[:absolute_start].encode('utf-8'))
    byte_end = len(text[:absolute_end].encode('utf-8'))
    if raw[byte_start:byte_end] != quote.encode('utf-8'):
        raise ValueError('byte_location')
    return {'sourceSha256': expected_sha256, **citation,
            'offsetUnit': 'unicode_code_points', 'sourceStart': absolute_start,
            'sourceEndExclusive': absolute_end, 'byteStart': byte_start,
            'byteEndExclusive': byte_end, 'meaning': 'exact_text_location_only',
            'authorityVerified': False}


RAW = '合成甲：命令未确认。\n\n合成乙🙂：时刻未知。\n'.encode('utf-8')
PIN = '8d898758ff7afcd50bbf55597b354be1b6c94a6a9dc8e43f7602078893f100f5'
NEW = '合成甲：命令已确认。\n\n合成乙🙂：时刻未知。\n'.encode('utf-8')
NEW_PIN = '33c287ec83d999d29c1b29d99671f6bca559b792ff1fc58314899824a8e78161'
CITATION = {'paragraph': 2, 'start': 3, 'length': 7, 'quote': '🙂：时刻未知。'}
# Emoji counts as one code point; the full quoted tail has seven code points.


class Checks(unittest.TestCase):
    def test_exact_tail_and_original_bytes(self):
        result = locate(RAW, CITATION, expected_sha256=PIN)
        self.assertEqual((result['sourceStart'], result['sourceEndExclusive']), (15, 22))
        self.assertEqual((result['byteStart'], result['byteEndExclusive']), (41, 63))
        self.assertEqual(RAW[41:63].decode('utf-8'), CITATION['quote'])
        self.assertNotIn('page', result)
        self.assertFalse(result['authorityVerified'])

    def test_new_text_rejects_old_pin_even_for_unchanged_tail(self):
        with self.assertRaisesRegex(ValueError, '^source_digest$'):
            locate(NEW, CITATION, expected_sha256=PIN)
        result = locate(NEW, CITATION, expected_sha256=NEW_PIN)
        self.assertEqual(result['sourceSha256'], NEW_PIN)

    def test_invalid_utf8_after_matching_digest(self):
        raw = b'\xff'
        with self.assertRaisesRegex(ValueError, '^utf8$'):
            locate(raw, CITATION, expected_sha256=hashlib.sha256(raw).hexdigest())

    def test_tail_overrun_and_wrong_locator(self):
        for patch in ({'length': 8}, {'length': 8, 'quote': CITATION['quote'] + 'X'},
                      {'start': 4}, {'paragraph': 1}, {'paragraph': True}, {'quote': ''}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                locate(RAW, {**CITATION, **patch}, expected_sha256=PIN)

    def test_no_extractor_identity_or_page(self):
        for patch in ({'sourceSha256': PIN}, {'page': 1}, {'position': [0, 0]}):
            with self.subTest(patch=patch), self.assertRaisesRegex(ValueError, '^citation_fields$'):
                locate(RAW, {**CITATION, **patch}, expected_sha256=PIN)

    def test_no_newline_normalization_or_page_inference(self):
        for raw in (RAW.replace(b'\n', b'\r\n'), b'\xef\xbb\xbf' + RAW, RAW + b'\f'):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, '^text_format$'):
                locate(raw, CITATION, expected_sha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaisesRegex(ValueError, '^empty_source$'):
            locate(b'\n \n', CITATION, expected_sha256=hashlib.sha256(b'\n \n').hexdigest())


if __name__ == '__main__':
    unittest.main(verbosity=2)
