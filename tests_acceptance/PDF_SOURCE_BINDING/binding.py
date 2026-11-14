"""Pure internal derivative binding; no custody commands, DB, API or authentication."""
import hashlib
import json
import re

class BindingError(ValueError):pass
HEX=re.compile(r'^[0-9a-f]{64}$')

def digest(data):return hashlib.sha256(data).hexdigest()
def canonical(doc):return json.dumps(doc,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def text(v):return type(v) is str and 0<len(v)<=256 and v==v.strip()
def sha(v):return type(v) is str and bool(HEX.fullmatch(v))
def need(ok):
    if not ok:raise BindingError('invalid binding')

def build(source, source_pdf_bytes, derivative):
    """Bind verified byte consistency, NOT authenticity/permissions/current DB state.

    No receipt/custody instruction is produced. Caller cannot use this artifact to
    overwrite source hashes. Registered and current source hashes remain distinct.
    """
    need(type(source_pdf_bytes) is bytes and len(source_pdf_bytes)<=8*1024*1024)
    need(type(source) is dict and set(source)=={'caseId','evidenceId','registeredSha256','expectedCurrentSha256','sourceStateDigest'})
    need(text(source['caseId']) and text(source['evidenceId']))
    need(all(sha(source[k]) for k in ('registeredSha256','expectedCurrentSha256','sourceStateDigest')))
    need(digest(source_pdf_bytes)==source['expectedCurrentSha256'])
    need(type(derivative) is dict)
    # Strict JSON round-trip snapshots arguments and rejects nonJSON objects.
    try:
        raw=canonical(derivative);need(len(raw)<=8*1024*1024)
        d=json.loads(raw)
    except (TypeError,ValueError,UnicodeError,RecursionError) as e:
        raise BindingError('invalid derivative JSON') from e
    need(set(d)=={'format','version','sourcePdfSha256','sourceByteLength','method','tool','parameters','pageCount','pages','warnings'})
    need(d['format']=='mcis-digital-pdf-text-layer' and type(d['version']) is int and d['version']==1)
    need(d['method']=='embedded_text_only' and d['sourcePdfSha256']==source['expectedCurrentSha256'])
    need(type(d['sourceByteLength']) is int and d['sourceByteLength']==len(source_pdf_bytes))
    need(text(d['tool']) and d['parameters']==['-layout','-enc','UTF-8'])
    need(type(d['pageCount']) is int and 1<=d['pageCount']<=100)
    need(type(d['pages']) is list and len(d['pages'])==d['pageCount'])
    need(type(d['warnings']) is list and 1<=len(d['warnings'])<=8 and all(type(w) is str and len(w)<=1000 for w in d['warnings']))
    for n,p in enumerate(d['pages'],1):
        need(type(p) is dict and set(p)=={'physicalPage','text','textSha256','byteLength','status'})
        need(type(p['physicalPage']) is int and p['physicalPage']==n and type(p['text']) is str)
        b=p['text'].encode('utf-8');need(len(b)<=512*1024)
        need(type(p['byteLength']) is int and p['byteLength']==len(b) and p['textSha256']==digest(b))
        need(p['status']==('text_layer_present' if p['text'].strip() else 'no_selectable_text'))
    body={'format':'mcis-pdf-text-binding','version':1,'canonicalization':'MCIS-JSON-UTF8-SORTED-V1',
          'sourceBinding':dict(source),'derivative':d,
          'derivativeContentSha256':digest(raw),
          'limitations':['Byte consistency only; not source authenticity, permissions, OCR or image understanding.',
                         'Not a custody Change or source replacement. Source hashes remain unchanged.']}
    return {**body,'artifactSha256':digest(canonical(body))}


def validate(artifact, source, source_pdf_bytes):
    need(type(artifact) is dict and 'derivative' in artifact)
    expected=build(source,source_pdf_bytes,artifact['derivative'])
    try:
        need(canonical(artifact)==canonical(expected))
    except (TypeError,ValueError,UnicodeError,RecursionError) as e:
        raise BindingError("invalid artifact JSON") from e
    return True
