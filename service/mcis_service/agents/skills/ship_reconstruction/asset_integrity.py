"""Research asset integrity binding; trusted manifest storage is required."""
import hashlib
import math
import json
import hmac
import re
import struct

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')

def validate_glb_framing(glb):
    # Restricted to the GLB 2.0 JSON + BIN profile produced by our exporter.
    if not isinstance(glb,bytes) or len(glb)<28:
        raise ValueError('truncated GLB')
    magic,version,length=struct.unpack_from('<4sII',glb)
    if magic!=b'glTF' or version!=2 or length!=len(glb):
        raise ValueError('invalid GLB header')
    pos=12
    for expected in (b'JSON',b'BIN\x00'):
        if pos+8>len(glb):
            raise ValueError('truncated GLB chunk header')
        size,kind=struct.unpack_from('<I4s',glb,pos)
        pos+=8
        if kind!=expected or size%4 or size==0 or pos+size>len(glb):
            raise ValueError('invalid GLB chunk framing')
        if expected==b'JSON':
            try:
                doc=json.loads(glb[pos:pos+size])
            except (ValueError, UnicodeError) as exc:
                raise ValueError('invalid GLB JSON') from exc
            if not isinstance(doc,dict) or not isinstance(doc.get('asset'),dict) or doc['asset'].get('version')!='2.0':
                raise ValueError('invalid GLB asset declaration')
        pos+=size
    if pos!=len(glb):
        raise ValueError('unexpected trailing GLB data')
    return doc

def bind_asset(glb, evidence, *, algorithm_version):
    doc=validate_glb_framing(glb)
    if not isinstance(algorithm_version,str) or not algorithm_version.strip():
        raise ValueError('algorithm version required')
    if not isinstance(evidence,dict) or evidence.get('research_only') is not True or evidence.get('lofting_authorized') is not False:
        raise ValueError('research evidence required')
    extras=doc['asset'].get('extras')
    if not isinstance(extras,dict) or extras.get('research_only') is not True or extras.get('lofting_authorized') is not False:
        raise ValueError('GLB authorization metadata inconsistent with research evidence')
    for metadata in (extras,evidence):
        if 'mcis_origin_m' in metadata:
            origin=metadata['mcis_origin_m']
            if not isinstance(origin,list) or len(origin)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in origin):
                raise ValueError('invalid GLB or sidecar local origin')
    if ('mcis_origin_m' in extras)!=('mcis_origin_m' in evidence) or extras.get('mcis_origin_m')!=evidence.get('mcis_origin_m'):
        raise ValueError('GLB local origin inconsistent with evidence')
    return dict(version='0.1',algorithm_version=algorithm_version,
                glb_sha256=hashlib.sha256(glb).hexdigest(),
                evidence_sha256=hashlib.sha256(canonical(evidence)).hexdigest(),
                research_only=True,lofting_authorized=False)

def verify_asset(glb,evidence,manifest,*,expected_algorithm_version):
    expected=bind_asset(glb,evidence,algorithm_version=expected_algorithm_version)
    if not isinstance(manifest,dict):
        return dict(matches=False,mismatches=['manifest'],authenticity_checked=False,lofting_authorized=False)
    mismatches=[]
    for k,v in expected.items():
        got=manifest.get(k)
        if type(got) is not type(v):
            mismatches.append(k)
        elif k.endswith('_sha256'):
            if re.fullmatch(r'[0-9a-f]{64}',got) is None or not hmac.compare_digest(got,v):
                mismatches.append(k)
        elif got!=v:
            mismatches.append(k)
    return dict(matches=not mismatches,mismatches=mismatches,authenticity_checked=False,lofting_authorized=False)
