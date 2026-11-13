"""Unpersisted provenance preview only. No model calls or publication."""
from dataclasses import dataclass
import hashlib
import json

class Invalid(ValueError):
    pass

def text(value, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise Invalid('INVALID_TEXT')
    try:
        value.encode('utf-8', errors='strict')
    except UnicodeError:
        raise Invalid('INVALID_UNICODE') from None
    if any(ord(c) < 32 and c not in '\n\t\r' for c in value):
        raise Invalid('INVALID_CONTROL')
    return value

def sha(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def digest(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')))

def exact(obj, keys):
    if not isinstance(obj, dict) or set(obj) != set(keys.split()):
        raise Invalid('INVALID_FIELDS')

def bounded_int(token):
    # Only citation offsets can be integers; text snapshots max out at 200000.
    # Bound before int() so Python's configurable digit ceiling cannot leak a
    # bare ValueError or permit expensive arbitrary-precision conversion.
    digits = token[1:] if token.startswith('-') else token
    if len(digits) > 6:
        raise Invalid('NUMBER_BUDGET')
    return int(token)


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise Invalid('DUPLICATE_KEY')
        result[key] = value
    return result

@dataclass(frozen=True)
class Source:
    source_id: str
    version: str
    source_type: str
    locator: str
    content: str

    def __post_init__(self):
        text(self.source_id, 160)
        text(self.version, 160)
        text(self.locator, 1000)
        text(self.content, 200000)
        if self.source_type not in ('Public', 'Synthetic'):
            raise Invalid('UNSUPPORTED_SOURCE_TYPE')

    @property
    def text_sha256(self):
        return sha(self.content)

def gate(raw, sources, known=()):
    if type(raw) is not bytes or len(raw) > 65536:
        raise Invalid('INPUT_BUDGET')
    if not isinstance(sources, (tuple, list)) or len(sources) > 16:
        raise Invalid('SOURCE_BUDGET')
    registry = {}
    for source in sources:
        if not isinstance(source, Source) or source.source_id in registry:
            raise Invalid('AMBIGUOUS_SOURCE')
        registry[source.source_id] = source
    if sum(len(s.content.encode('utf-8')) for s in sources) > 524288:
        raise Invalid('SOURCE_BUDGET')
    seen = set()
    for value in known:
        if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise Invalid('INVALID_PRIOR_FINGERPRINT')
        seen.add(value)
    try:
        body = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_int=bounded_int,
                          parse_constant=lambda _: (_ for _ in ()).throw(Invalid('NONFINITE')))
    except Invalid:
        raise
    except (ValueError, RecursionError):
        raise Invalid('INVALID_JSON') from None
    exact(body, 'candidates')
    candidates = body['candidates']
    if type(candidates) is not list or len(candidates) > 32:
        raise Invalid('CANDIDATE_BUDGET')
    result, duplicates = [], []
    for index, item in enumerate(candidates):
        exact(item, 'kind title claim citations')
        if item['kind'] not in ('Case', 'Challenge', 'Method'):
            raise Invalid('INVALID_KIND')
        text(item['title'], 160)
        text(item['claim'], 4000)
        citations = item['citations']
        if type(citations) is not list or not 1 <= len(citations) <= 8:
            raise Invalid('CITATION_BUDGET')
        pinned, types = [], set()
        for citation in citations:
            exact(citation, 'sourceId version textSha256 start end quote')
            source_id = text(citation['sourceId'], 160)
            source = registry.get(source_id)
            if source is None:
                raise Invalid('UNKNOWN_SOURCE')
            if citation['version'] != source.version or citation['textSha256'] != source.text_sha256:
                raise Invalid('STALE_SOURCE')
            start, end = citation['start'], citation['end']
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(source.content):
                raise Invalid('INVALID_SPAN')
            quote = text(citation['quote'], 10000)
            if source.content[start:end] != quote:
                raise Invalid('QUOTE_MISMATCH')
            types.add(source.source_type)
            pinned.append(dict(citation, sourceType=source.source_type, locator=source.locator))
        payload = dict(kind=item['kind'], title=item['title'], claim=item['claim'], citations=pinned)
        fingerprint = digest(payload)
        if fingerprint in seen:
            duplicates.append(dict(index=index, fingerprint=fingerprint))
            continue
        seen.add(fingerprint)
        result.append(dict(payload, fingerprint=fingerprint, status='CandidatePreview',
                           sourceTypes=sorted(types), synthetic='Synthetic' in types,
                           reviewRequired=True, factualStatus='Unverified'))
    return dict(profile='MCIS-KNOWLEDGE-CANDIDATE-GATE-1', persisted=False, modelUsed=False,
                publicationAllowed=False, candidates=result, duplicates=duplicates,
                warning='摘录定位一致不代表主张成立；来源、使用权、事实与发布仍须人工审核。')
