"""Research asset integrity binding; trusted manifest storage is required."""
import hashlib
import json
import hmac

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')

def bind_asset(glb, evidence, *, algorithm_version):
    if not isinstance(glb,bytes) or not glb.startswith(b'glTF'):
        raise ValueError('GLB bytes required')
    if not isinstance(algorithm_version,str) or not algorithm_version.strip():
        raise ValueError('algorithm version required')
    if evidence.get('research_only') is not True or evidence.get('lofting_authorized') is not False:
        raise ValueError('research evidence required')
    return dict(version='0.1',algorithm_version=algorithm_version,
                glb_sha256=hashlib.sha256(glb).hexdigest(),
                evidence_sha256=hashlib.sha256(canonical(evidence)).hexdigest(),
                research_only=True,lofting_authorized=False)

def verify_asset(glb,evidence,manifest,*,expected_algorithm_version):
    expected=bind_asset(glb,evidence,algorithm_version=expected_algorithm_version)
    mismatches=[k for k,v in expected.items() if type(manifest.get(k)) is not type(v) or (not hmac.compare_digest(manifest[k],v) if k.endswith('_sha256') else manifest[k]!=v)]
    return dict(matches=not mismatches,mismatches=mismatches,authenticity_checked=False,lofting_authorized=False)
