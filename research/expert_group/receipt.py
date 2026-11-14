"""Metadata-only local receipt chain; not a signature or identity proof."""
import hashlib
import json
import os
import re


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


class Receipt:
    FIELDS = {'phase', 'groupRunId', 'roleId', 'runId', 'modelCalls', 'toolCalls',
              'errorCode', 'attempt', 'providerRequests', 'packetSha256',
              'manifestDigest', 'outputDigest', 'inputDigest', 'toolName', 'toolCallId', 'transportMocked', 'status', 'outcome'}
    def __init__(self, path, *, dir_fd=None):
        self.fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=dir_fd)
        self.previous = '0' * 64
        self.sequence = 0
        self.file_hash = hashlib.sha256()

    def append(self, event):
        if type(event) is not dict or not set(event) <= self.FIELDS or 'phase' not in event:
            raise ValueError('receipt metadata')
        for key, value in event.items():
            if key in {'modelCalls', 'toolCalls', 'attempt', 'providerRequests'}:
                if type(value) is not int or not 0 <= value <= 32: raise ValueError('receipt count')
            elif key == 'transportMocked':
                if type(value) is not bool: raise ValueError('receipt flag')
            elif type(value) is not str or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', value):
                raise ValueError('receipt token')
        if self.sequence >= 256: raise ValueError('receipt budget')
        row = {'schemaVersion': 1, 'seq': self.sequence + 1, 'previousSha256': self.previous, 'event': event}
        digest = hashlib.sha256(canonical(row)).hexdigest()
        raw = canonical({**row, 'sha256': digest}) + b'\n'
        # Handle short writes; a partial error leaves an incomplete chain, never success.
        view = memoryview(raw)
        while view:
            count = os.write(self.fd, view)
            if not count: raise OSError('receipt write')
            view = view[count:]
        os.fsync(self.fd)
        self.file_hash.update(raw)
        self.sequence += 1
        self.previous = digest

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


def write_new(path, content, *, dir_fd=None):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=dir_fd)
    try:
        stream = os.fdopen(fd, 'wb')
        fd = None  # Ownership transfers only after wrapping succeeds.
        with stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if fd is not None:
            os.close(fd)


def verify_export(directory):
    """Verify local export consistency only, never author/provider authenticity."""
    import stat
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    def read(name, limit):
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode): raise ValueError('regular file required')
            stream = os.fdopen(fd, 'rb')
            fd = None  # A failed fdopen leaves the raw descriptor owned here.
            with stream:
                raw = stream.read(limit+1)
        finally:
            if fd is not None:
                os.close(fd)
        if len(raw) > limit: raise ValueError('artifact budget')
        return raw
    def parse(raw):
        def pairs(items):
            obj = {}
            for key, value in items:
                if key in obj: raise ValueError('duplicate key')
                obj[key] = value
            return obj
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))
    try:
        marker = parse(read('completion.json', 4096))
        if set(marker) != {'schemaVersion','exportStatus','runId','runStatus','resultSha256','htmlSha256','receiptSha256'} or type(marker['schemaVersion']) is not int or marker['schemaVersion'] != 1 or marker['exportStatus'] != 'complete':
            raise ValueError('completion schema')
        result_raw = read('result.json', 8*1024*1024)
        html_raw = read('comparison.html', 8*1024*1024)
        receipt_raw = read('receipt.jsonl', 1024*1024)
        for key, raw in [('resultSha256', result_raw), ('htmlSha256', html_raw), ('receiptSha256', receipt_raw)]:
            if hashlib.sha256(raw).hexdigest() != marker[key]: raise ValueError('artifact mismatch')
        result = parse(result_raw)
        if (result['runId'] != marker['runId'] or result['status'] != marker['runStatus'] or
            result.get('artifactPolicy') != 'incomplete_without_valid_completion_manifest' or
            result.get('factActivated') is not False or result.get('consensusComputed') is not False):
            raise ValueError('result mismatch')
        previous = '0'*64
        rows = receipt_raw.splitlines()
        if not 1 <= len(rows) <= 256 or not receipt_raw.endswith(b'\n'): raise ValueError('receipt incomplete')
        for seq, raw in enumerate(rows, 1):
            row = parse(raw)
            if set(row) != {'schemaVersion','seq','previousSha256','event','sha256'} or row['schemaVersion'] != 1 or type(row['seq']) is not int or row['seq'] != seq or row['previousSha256'] != previous:
                raise ValueError('receipt chain')
            digest = row.pop('sha256')
            if hashlib.sha256(canonical(row)).hexdigest() != digest: raise ValueError('receipt hash')
            previous = digest
        event = row['event']
        if (event.get('phase') != 'artifacts_written' or event.get('groupRunId') != result['runId'] or
            event.get('status') != result['status'] or event.get('outputDigest') != marker['resultSha256']):
            raise ValueError('receipt terminal')
        return {'exportStatus': 'verified_local_consistency', 'runId': marker['runId'],
                'runStatus': marker['runStatus'], 'authenticityVerified': False,
                'transportMocked': result['transportMocked'], 'factActivated': False}
    finally:
        os.close(descriptor)
