"""Explicit local public-report source declarations; no network or model."""
import argparse
import hashlib
import ipaddress
import json
import os
import re
import stat
import sys
from datetime import date
from urllib.parse import urlsplit

MAX_MANIFEST = 65536
MAX_FILE = 8 * 1024 * 1024
PROFILE = 'MCIS-PUBLIC-REPORT-MANIFEST-1'

class Invalid(ValueError):
    pass

def exact(obj, fields):
    if type(obj) is not dict or set(obj) != set(fields.split()):
        raise Invalid('INVALID_FIELDS')

def text(v, limit):
    if not isinstance(v, str) or not v.strip() or len(v) > limit:
        raise Invalid('INVALID_TEXT')
    try: v.encode('utf-8')
    except UnicodeError: raise Invalid('INVALID_TEXT') from None
    if any(ord(c) < 32 for c in v): raise Invalid('INVALID_TEXT')

def pairs(items):
    d = {}
    for k, v in items:
        if k in d: raise Invalid('DUPLICATE_KEY')
        d[k] = v
    return d

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def decode(raw):
    if type(raw) is not bytes or len(raw) > MAX_MANIFEST: raise Invalid('MANIFEST_BUDGET')
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(Invalid('INVALID_JSON')))
    except (ValueError, RecursionError, UnicodeError):
        raise Invalid('INVALID_JSON') from None

def preview(manifest_raw, pdf_raw):
    if type(pdf_raw) is not bytes or not 5 <= len(pdf_raw) <= MAX_FILE:
        raise Invalid('FILE_BUDGET')
    if not pdf_raw.startswith(b'%PDF-'): raise Invalid('PDF_MARKER_REQUIRED')
    m = decode(manifest_raw)
    exact(m, 'profile title publisher sourceUrl publicationDate fileSha256 locators')
    if m['profile'] != PROFILE: raise Invalid('UNKNOWN_PROFILE')
    text(m['title'], 300);text(m['publisher'], 200);text(m['sourceUrl'], 2000)
    try:
        u = urlsplit(m['sourceUrl']); host = (u.hostname or '').rstrip('.')
        valid = u.scheme == 'https' and '.' in host and not u.username and not u.password and u.port in (None, 443)
        valid = valid and not u.query and not u.fragment and '?' not in m['sourceUrl'] and '#' not in m['sourceUrl']
        valid = valid and host != 'localhost' and not host.endswith(('.local', '.localhost')) and not any(c.isspace() for c in m['sourceUrl']) and '\\' not in m['sourceUrl']
        try: valid = valid and ipaddress.ip_address(host).is_global
        except ValueError:
            if re.fullmatch(r'[0-9.]+', host): valid = False
        if not valid: raise ValueError()
    except ValueError: raise Invalid('PUBLIC_HTTPS_URL_REQUIRED') from None
    if m['publicationDate'] is not None:
        if not isinstance(m['publicationDate'], str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', m['publicationDate']): raise Invalid('INVALID_DATE')
        try: date.fromisoformat(m['publicationDate'])
        except ValueError: raise Invalid('INVALID_DATE') from None
    if not isinstance(m['fileSha256'], str) or not re.fullmatch('[a-f0-9]{64}', m['fileSha256']): raise Invalid('INVALID_DIGEST')
    if m['fileSha256'] != sha(pdf_raw): raise Invalid('FILE_DIGEST_MISMATCH')
    locators = m['locators']
    if type(locators) is not list or not 1 <= len(locators) <= 200: raise Invalid('LOCATOR_BUDGET')
    seen = set()
    for row in locators:
        exact(row, 'pdfPage printedPage label')
        if type(row['pdfPage']) is not int or not 1 <= row['pdfPage'] <= 10000: raise Invalid('INVALID_PAGE')
        if row['printedPage'] is not None: text(row['printedPage'], 80)
        text(row['label'], 500)
        key = encode(row)
        if key in seen: raise Invalid('DUPLICATE_LOCATOR')
        seen.add(key)
    return {'profile': 'MCIS-PUBLIC-REPORT-PREVIEW-1', 'manifest': m,
            'manifestDigest': sha(encode(m)), 'fileSha256': sha(pdf_raw), 'byteLength': len(pdf_raw),
            'modelUsed': False, 'networkUsed': False, 'caseWritten': False,
            'sourceAuthenticity': 'not_verified', 'pdfStructureValidated': False,
            'pageLocatorsVerified': False, 'reviewRequired': True,
            'warning': '文件摘要匹配不证明来源真实性、PDF有效性或页码内容正确。发布者、日期、URL和页码均为录入声明，须人工核实。'}

def parent_fd(path):
    if not hasattr(os, 'O_NOFOLLOW') or not hasattr(os, 'O_DIRECTORY'): raise Invalid('SAFE_FILE_ACCESS_UNAVAILABLE')
    if '..' in os.fspath(path).split(os.sep): raise Invalid('PARENT_PATH_REJECTED')
    absolute = os.path.abspath(path);parts = absolute.split(os.sep)
    fd = os.open(os.sep, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in parts[1:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd);fd = nxt
        return fd, parts[-1]
    except BaseException:
        os.close(fd);raise

def read_file(path, limit):
    parent, name = parent_fd(path)
    try: fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally: os.close(parent)
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode): raise Invalid('REGULAR_FILE_REQUIRED')
        data = stream.read(limit + 1)
    if len(data) > limit: raise Invalid('FILE_BUDGET')
    return data

def main(argv=None):
    p = argparse.ArgumentParser(description='Explicit local source declarations; not source authentication or PDF parsing.')
    p.add_argument('--manifest', required=True);p.add_argument('--pdf', required=True);p.add_argument('--output', required=True)
    a = p.parse_args(argv)
    try:
        result = preview(read_file(a.manifest, MAX_MANIFEST), read_file(a.pdf, MAX_FILE))
        data = encode(result) + b'\n'
        parent, name = parent_fd(a.output)
        try: fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        finally: os.close(parent)
        with os.fdopen(fd, 'wb') as f: f.write(data);f.flush();os.fsync(f.fileno())
        return 0
    except Invalid as e:
        print('Source preview rejected: ' + str(e), file=sys.stderr);return 4
    except OSError:
        print('Source preview I/O failed; output is unverified and may be incomplete. No overwrite or retry.', file=sys.stderr);return 3

if __name__ == '__main__': raise SystemExit(main())
