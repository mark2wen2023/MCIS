"""Pinned public test packet and review shape checks; no execution or credentials."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PACKET_SHA256 = '1dc5f6ccd93da013863abfd399b8e3f8682d2532e62d335eaa23cd5e18d8790e'

ROLES = ('source_attribution', 'uncertainty_boundary')

def _dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)

def _digest(value):
    return hashlib.sha256(_dump(value).encode('utf-8')).hexdigest()

class GroupError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)

def _strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise GroupError('duplicate_key')
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(GroupError('nonfinite_json')))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise GroupError('invalid_json') from None

def load_packet():
    return (ROOT / 'public-packet.json').read_bytes()

def _packet(raw):
    if not isinstance(raw, bytes) or hashlib.sha256(raw).hexdigest() != PACKET_SHA256:
        raise GroupError('packet_pin_mismatch')
    packet = _strict(raw.decode('utf-8'))
    if set(packet) != {'schemaVersion','meaning','items'} or type(packet['schemaVersion']) is not int or packet['schemaVersion'] != 1:
        raise GroupError('packet_schema')
    if packet['meaning'] != 'public_report_excerpt_declarations_not_verified_facts' or len(packet['items']) != 3:
        raise GroupError('packet_schema')
    for index, item in enumerate(packet['items'], 1):
        if set(item) != {'itemId','claim','sourceText','sourceSha256','sourceLocator','citation'} or item['itemId'] != f'item_{index:03d}': raise GroupError('packet_schema')
        if hashlib.sha256(item['sourceText'].encode('utf-8')).hexdigest() != item['sourceSha256']: raise GroupError('source_digest')
        citation = item['citation']
        if set(citation) != {'start','length','quote'} or type(citation['start']) is not int or type(citation['length']) is not int or citation['start'] < 0 or citation['length'] <= 0 or item['sourceText'][citation['start']:citation['start']+citation['length']] != citation['quote']: raise GroupError('source_quote')
        locator = item['sourceLocator']
        if set(locator) != {'url','pdfSha256','pdfPage','printedPage','section'} or locator['pdfPage'] != 28 or locator['printedPage'] != 26 or locator['url'] != 'https://www.sh.msa.gov.cn/u/cms/www/202505/191445221747637122775.pdf' or locator['pdfSha256'] != '99084b8e672da6e2f8d9809bea25a92fe5fcf31c318554832e14339610015d7f': raise GroupError('source_locator')
    return packet

def _validate(args, packet):
    if not isinstance(args, dict) or set(args) != {'reviews'} or not isinstance(args['reviews'], list) or len(args['reviews']) != len(packet['items']): raise GroupError('review_schema')
    seen = set()
    sources = {i['itemId']:i for i in packet['items']}
    for review in args['reviews']:
        if not isinstance(review,dict) or set(review) != {'itemId','label','rationale','uncertainty','quote'}: raise GroupError('review_schema')
        if any(not isinstance(v,str) or not v.strip() or len(v)>12000 for v in review.values()): raise GroupError('review_schema')
        try: _dump(review).encode('utf-8')
        except UnicodeError: raise GroupError('review_schema') from None
        item_id = review['itemId']
        if item_id not in sources or item_id in seen or review['label'] not in ('supported','conflicted','insufficient'): raise GroupError('review_schema')
        if review['quote'] not in sources[item_id]['sourceText']: raise GroupError('review_quote')
        seen.add(item_id)
    return args['reviews']
