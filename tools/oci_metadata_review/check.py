"""Read-only narrow OCI metadata review; never extracts, loads or approves images."""
import argparse
import hashlib
import json
import os
import re
import stat

MAX_ARCHIVE = 8 * 1024**3
MAX_METADATA = 1024**2
MAX_MEMBERS = 4096
MANIFEST = 'application/vnd.oci.image.manifest.v1+json'
CONFIG = 'application/vnd.oci.image.config.v1+json'
LAYER = 'application/vnd.oci.image.layer.v1.tar+gzip'
HEX = re.compile(r'[0-9a-f]{64}')

class Rejected(Exception):
    pass

def need(condition, code):
    if not condition:
        raise Rejected(code)

def decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, 'JSON_DUPLICATE')
            result[key] = value
        return result
    def constant(_):
        raise Rejected('JSON_FORMAT')
    need(len(raw) <= MAX_METADATA, 'METADATA_LIMIT')
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError):
        raise Rejected('JSON_FORMAT') from None

def keys(value, required, optional=()):
    need(isinstance(value, dict) and set(required) <= set(value)
         and set(value) <= set(required) | set(optional), 'UNSUPPORTED_METADATA')

def octal(raw):
    field = raw.rstrip(b'\0 ').lstrip(b' ')
    need(bool(re.fullmatch(b'[0-7]+', field)), 'TAR_NUMBER')
    return int(field, 8)

def scan(f, length):
    """Only regular USTAR headers; no PAX/GNU extensions or implicit paths."""
    members = {}
    while True:
        need(f.tell() + 512 <= length, 'TAR_TRUNCATED')
        header = f.read(512)
        need(len(header) == 512, 'TAR_TRUNCATED')
        if header == bytes(512):
            need(f.read(512) == bytes(512), 'TAR_END')
            remaining = length - f.tell()
            need(remaining >= 0, 'TAR_END')
            while remaining:
                tail = f.read(min(remaining, 1024**2))
                need(bool(tail) and not any(tail), 'TAR_TRAILING')
                remaining -= len(tail)
            need(not f.read(1), 'INPUT_CHANGED')
            return members
        need(len(members) < MAX_MEMBERS, 'MEMBER_LIMIT')
        need(header[257:265] == b'ustar\x0000' and not any(header[345:]), 'UNSUPPORTED_TAR')
        need(header[156:157] in (b'0', b'\0') and not any(header[157:257]), 'MEMBER_TYPE')
        need(octal(header[148:156]) == sum(header[:148]) + 8*32 + sum(header[156:]), 'TAR_CHECKSUM')
        name_bytes = header[:100].split(b'\0', 1)[0]
        need(header[:100] == name_bytes.ljust(100, b'\0'), 'MEMBER_PATH')
        try:
            name = name_bytes.decode('ascii')
        except UnicodeError:
            raise Rejected('MEMBER_PATH') from None
        need(name in ('oci-layout', 'index.json') or re.fullmatch(r'blobs/sha256/[0-9a-f]{64}', name), 'MEMBER_PATH')
        need(name not in members, 'MEMBER_DUPLICATE')
        size = octal(header[124:136]); offset = f.tell()
        need(size <= MAX_ARCHIVE and offset + size + (-size % 512) <= length, 'MEMBER_SIZE')
        if name in ('oci-layout', 'index.json'):
            need(size <= MAX_METADATA, 'METADATA_LIMIT')
        h = hashlib.sha256(); remaining = size
        while remaining:
            chunk = f.read(min(remaining, 1024**2))
            need(bool(chunk), 'TAR_TRUNCATED'); h.update(chunk); remaining -= len(chunk)
        need(not any(f.read(-size % 512)), 'TAR_PADDING')
        digest = h.hexdigest()
        if name.startswith('blobs/'):
            need(digest == name.rsplit('/', 1)[1], 'BLOB_HASH')
        members[name] = (offset, size, digest)

def metadata(f, members, name):
    need(name in members, 'MEMBER_MISSING')
    offset, size, _ = members[name]
    need(size <= MAX_METADATA, 'METADATA_LIMIT')
    f.seek(offset)
    return decode(f.read(size))

def descriptor(d, media_type, members, used, platform=False):
    keys(d, ('mediaType', 'digest', 'size') + (('platform',) if platform else ()))
    need(d['mediaType'] == media_type, 'UNSUPPORTED_MEDIA_TYPE')
    digest = d['digest']
    need(isinstance(digest, str) and re.fullmatch(r'sha256:[0-9a-f]{64}', digest), 'DESCRIPTOR_DIGEST')
    need(type(d['size']) is int and d['size'] > 0, 'DESCRIPTOR_SIZE')
    name = 'blobs/sha256/' + digest[7:]
    need(name in members, 'MEMBER_MISSING')
    need(members[name][1:] == (d['size'], digest[7:]), 'DESCRIPTOR_MISMATCH')
    used.add(name)
    return name

def inspect_metadata(f, members, target):
    need(metadata(f, members, 'oci-layout') == {'imageLayoutVersion':'1.0.0'}, 'UNSUPPORTED_LAYOUT')
    index = metadata(f, members, 'index.json')
    keys(index, ('schemaVersion', 'manifests'), ('mediaType',))
    need(type(index['schemaVersion']) is int and index['schemaVersion'] == 2, 'UNSUPPORTED_INDEX')
    need(index.get('mediaType', 'application/vnd.oci.image.index.v1+json') == 'application/vnd.oci.image.index.v1+json', 'UNSUPPORTED_INDEX')
    need(isinstance(index['manifests'], list) and len(index['manifests']) == 1, 'AMBIGUOUS_PLATFORM')
    used = {'oci-layout', 'index.json'}
    d = index['manifests'][0]
    manifest_name = descriptor(d, MANIFEST, members, used, platform=True)
    parts = target.split('/')
    expected = dict(os=parts[0], architecture=parts[1])
    if len(parts) == 3:
        expected['variant'] = parts[2]
    need(d['platform'] == expected, 'PLATFORM_MISMATCH')
    manifest = metadata(f, members, manifest_name)
    keys(manifest, ('schemaVersion', 'mediaType', 'config', 'layers'))
    need(type(manifest['schemaVersion']) is int and manifest['schemaVersion'] == 2 and manifest['mediaType'] == MANIFEST, 'UNSUPPORTED_MANIFEST')
    config_name = descriptor(manifest['config'], CONFIG, members, used)
    layers = manifest['layers']
    need(isinstance(layers, list) and 0 < len(layers) <= MAX_MEMBERS-4, 'LAYER_LIMIT')
    for layer in layers:
        descriptor(layer, LAYER, members, used)
    config = metadata(f, members, config_name)
    need(isinstance(config, dict) and all(config.get(k) == v for k,v in expected.items()), 'CONFIG_PLATFORM')
    need('variant' in expected or 'variant' not in config, 'CONFIG_PLATFORM')
    rootfs = config.get('rootfs')
    keys(rootfs, ('type','diff_ids'))
    need(rootfs['type'] == 'layers' and isinstance(rootfs['diff_ids'], list)
         and len(rootfs['diff_ids']) == len(layers) and all(isinstance(x,str) and re.fullmatch(r'sha256:[0-9a-f]{64}',x) for x in rootfs['diff_ids']), 'ROOTFS_DECLARATION')
    need(set(members) == used, 'UNREFERENCED_MEMBER')
    return {'manifestDigest': d['digest'], 'configDigest': manifest['config']['digest'],
            'layers': len(layers), 'members':len(members)}

def review(path, expected_sha, expected_size, platform='linux/amd64'):
    need(isinstance(expected_sha,str) and HEX.fullmatch(expected_sha), 'INPUT_DIGEST')
    need(type(expected_size) is int and 1024 <= expected_size <= MAX_ARCHIVE and expected_size % 512 == 0, 'ARCHIVE_LIMIT')
    need(platform in ('linux/amd64','linux/arm64/v8'), 'UNSUPPORTED_PLATFORM')
    need(hasattr(os,'O_NOFOLLOW') and hasattr(os,'O_NONBLOCK'), 'HOST_UNSUPPORTED')
    # One descriptor, no symlink following; callers must own a stable directory.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as f:
        before = os.fstat(f.fileno())
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'INPUT_TYPE')
        need(before.st_size == expected_size, 'ARCHIVE_SIZE')
        h = hashlib.sha256(); remaining = expected_size
        while remaining:
            chunk = f.read(min(remaining,1024**2)); need(bool(chunk), 'INPUT_CHANGED')
            h.update(chunk); remaining -= len(chunk)
        need(not f.read(1) and h.hexdigest() == expected_sha, 'ARCHIVE_HASH')
        f.seek(0); members = scan(f, expected_size)
        result = inspect_metadata(f, members, platform)
        after = os.fstat(f.fileno())
        fields = ('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_nlink')
        need(all(getattr(before,k)==getattr(after,k) for k in fields), 'INPUT_CHANGED')
    return dict(schema='mcis.oci-metadata-review/1', result='metadata_checked',
        archiveSha256=expected_sha, archiveSize=expected_size, platform=platform, **result,
        runtimeApproved=False, inventoryVerified=False, rootfsDiffIdsVerified=False,
        dependencyAbiVerified=False, provenanceVerified=False, builderVerified=False)

class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Rejected('ARGUMENTS')

def main():
    try:
        p=Parser(description=__doc__)
        p.add_argument('--archive',required=True); p.add_argument('--sha256',required=True)
        p.add_argument('--size',required=True,type=int); p.add_argument('--platform',default='linux/amd64')
        a=p.parse_args()
        result=review(a.archive,a.sha256,a.size,a.platform)
    except Rejected as e:
        result={'schema':'mcis.oci-metadata-review/1','result':'rejected','code':str(e)}
    except OSError:
        result={'schema':'mcis.oci-metadata-review/1','result':'rejected','code':'INPUT_IO'}
    print(json.dumps(result,sort_keys=True,separators=(',',':')))
    return 0 if result['result']=='metadata_checked' else 2

if __name__ == '__main__':
    raise SystemExit(main())
