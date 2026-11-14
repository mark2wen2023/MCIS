"""Managed proxy policy boundary. Production bootstrap is deliberately unavailable.

No env discovery occurs until a trusted platform binding has been obtained. The
normalised policy below is our proposed contract, NOT a claimed platform API.
"""
from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
import re
import ssl
import stat
import time
from urllib.parse import urlsplit

TARGET='https://api.deepseek.com:443/chat/completions'
NETWORK_NAMES=frozenset({'HTTP_PROXY','HTTPS_PROXY','http_proxy','https_proxy','NO_PROXY','no_proxy','SSL_CERT_FILE','REQUESTS_CA_BUNDLE'})
FORBIDDEN_NAMES=frozenset({'ALL_PROXY','all_proxy','SSL_CERT_DIR','CURL_CA_BUNDLE'})

class ManagedError(ValueError):
    pass


def require(ok):
    if not ok:raise ManagedError('managed_binding_invalid')


def platform_binding(reference):
    """A future reviewed control-plane bridge must supply current authenticated metadata.

    Never replace this with env JSON, a caller-supplied URL, or a self-declared
    ready flag. No such supported bootstrap is available in this environment.
    """
    raise ManagedError('platform_binding_unavailable')


@dataclass(frozen=True,repr=False)
class Material:
    reference: str
    config_digest: str
    proxy: str
    context: ssl.SSLContext
    environment: dict

    def __repr__(self):return '<ManagedMaterial redacted>'


def _ca_bytes(path):
    require(type(path) is str and path.startswith('/') and len(path)<=4096)
    parent=fd=None
    try:
        parts=Path(path).parts;parent=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
        for part in parts[1:-1]:
            new=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
            os.close(parent);parent=new
        fd=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        st=os.fstat(fd);require(stat.S_ISREG(st.st_mode) and 0<st.st_size<=2*1024*1024)
        raw=bytearray()
        while len(raw)<=2*1024*1024:
            chunk=os.read(fd,min(65536,2*1024*1024+1-len(raw)))
            if not chunk:break
            raw.extend(chunk)
        require(0<len(raw)<=2*1024*1024 and b'PRIVATE KEY' not in raw)
        return bytes(raw)
    except Exception:
        raise ManagedError('managed_ca_invalid') from None
    finally:
        if fd is not None:os.close(fd)
        if parent is not None:os.close(parent)


def _validate(binding,reference,environment,*,now=None):
    """Private, testable normalisation boundary; input provenance is platform_binding's job."""
    try:
        require(type(binding) is dict and set(binding)=={'schema','reference','environmentId','runtimeEnvironmentId','sourceConfigId','sourceConfigVersion','specRevision','observedRevision','observationsCurrent','state','expiresAt','revoked','target','method','injectionMode','injectionHeader','environmentSha256','caSha256'})
        require(binding['schema']=='mcis.managed-network-binding.v1' and binding['reference']==reference)
        for k in ['reference','environmentId','runtimeEnvironmentId','sourceConfigId','sourceConfigVersion','specRevision','observedRevision']:
            require(type(binding[k]) is str and re.fullmatch(r'[a-zA-Z0-9._:-]{1,200}',binding[k]) is not None)
        require(binding['environmentId']==binding['runtimeEnvironmentId'] and binding['specRevision']==binding['observedRevision'])
        require(binding['observationsCurrent'] is True and binding['state']=='ready' and binding['revoked'] is False)
        current=time.time() if now is None else now
        require(type(binding['expiresAt']) in {int,float} and math.isfinite(binding['expiresAt']) and current<binding['expiresAt']<=current+3600)
        require(binding['target']==TARGET and binding['method']=='POST' and binding['injectionMode']=='proxy_header_injection' and binding['injectionHeader']=='Authorization')
        pins=binding['environmentSha256'];require(type(pins) is dict and set(pins)<=NETWORK_NAMES)
        require('HTTPS_PROXY' in pins and 'SSL_CERT_FILE' in pins and not(FORBIDDEN_NAMES & set(environment)))
        require({k for k in NETWORK_NAMES if k in environment}==set(pins))
        values={}
        for k,sha in pins.items():
            require(type(sha) is str and re.fullmatch('[a-f0-9]{64}',sha) is not None)
            value=environment[k];require(type(value) is str and len(value)<=8192 and not any(ord(c)<32 or ord(c)==127 for c in value))
            require(hashlib.sha256(value.encode()).hexdigest()==sha);values[k]=value
        proxy=values['HTTPS_PROXY'];parsed=urlsplit(proxy)
        require(parsed.scheme in {'http','https'} and parsed.hostname is not None and parsed.username is None and parsed.password is None and not parsed.query and not parsed.fragment and parsed.path in {'','/'})
        require(parsed.port is not None and 1<=parsed.port<=65535 and parsed.hostname.isascii())
        for name in ['HTTP_PROXY','http_proxy','https_proxy']:
            if name in values:require(values[name]==proxy)
        if 'NO_PROXY' in values and 'no_proxy' in values:require(values['NO_PROXY']==values['no_proxy'])
        for name in ['NO_PROXY','no_proxy']:
            for token in values.get(name,'').lower().split(','):
                host=token.strip().split(':')[0].lstrip('.')
                require(host!='*' and not(host and ('api.deepseek.com'==host or 'api.deepseek.com'.endswith('.'+host))))
        if 'REQUESTS_CA_BUNDLE' in values:require(values['REQUESTS_CA_BUNDLE']==values['SSL_CERT_FILE'])
        raw=_ca_bytes(values['SSL_CERT_FILE'])
        require(hashlib.sha256(raw).hexdigest()==binding['caSha256'])
        context=ssl.create_default_context(cadata=raw.decode('ascii'))
        require(context.check_hostname and context.verify_mode==ssl.CERT_REQUIRED)
        import json
        digest=hashlib.sha256(json.dumps(binding,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        return Material(reference,digest,proxy,context,values)
    except Exception:
        raise ManagedError('managed_binding_invalid') from None


def resolve(reference):
    if type(reference) is not str or re.fullmatch(r'[a-zA-Z0-9._:-]{1,200}',reference) is None:
        raise ManagedError('managed_reference_invalid')
    binding=platform_binding(reference) # Always fails closed until trusted bootstrap exists.
    return _validate(binding,reference,os.environ)
