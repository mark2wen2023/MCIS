"""Read-only operation-bound product-layout observation, never a readiness gate.
Only isolated synthetic directories are currently supported/validated.
"""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sqlite3
import stat
from mcis_service.package_intake.parser import read_bounded

LAYOUT = 'mcis-raw-evidence-source-v1-research'
MARKER = '_package_intake/operation.json'


def layout_files(raw):
    """Mirror mcase.import_case's raw/evidence file subset + retained intake ZIP.

    Does not cover working-record attachments or activate experimental imports.
    Caller must separately validate the experimental envelope and DB reconstruction.
    """
    members = read_bounded(raw)
    result = {p: b for p, b in members.items()
              if p.startswith(('raw/', 'evidence/')) and
              not p.endswith('/.keep') and p != 'evidence/index.json'}
    result['_package_intake/source.mcase'] = raw
    for path in result:
        parts = PurePosixPath(path).parts
        if not parts or any(p in ('..', '.', '') for p in parts) or path.startswith('/') or '\\' in path:
            raise ValueError('invalid layout path')
    return result


def operation_marker(operation_id, case_id, source_sha256):
    return {'layout': LAYOUT, 'operationId': operation_id,
            'caseId': case_id, 'sourceSha256': source_sha256}


def inspect_publication(db_path, operation_id, case_directory):
    """Observe one SQLite read snapshot and files; NOT a synchronized FS snapshot.

    No writes/retry/delete, no case visibility decision. Exact file set required.
    Local concurrent directory mutation is not covered: matching is observational,
    never permission, original authenticity, atomic publication or product readiness.
    """
    result = dict(status='unknown', dbCommitObserved=False, layoutObserved=False,
                  restore_ready=False, retryAllowed=False, deleteAllowed=False)
    try:
        with closing(sqlite3.connect(Path(db_path).absolute().as_uri()+'?mode=ro', uri=True, timeout=1)) as c:
            c.execute('PRAGMA query_only=ON'); c.execute('BEGIN')
            claim = c.execute('SELECT case_id,source_sha256,attempts FROM offline_restore_operation WHERE operation_id=?', (operation_id,)).fetchone()
            commit = c.execute('SELECT case_id,source_sha256 FROM offline_restore_commit WHERE operation_id=?', (operation_id,)).fetchone()
            if claim is None: return result
            if commit is None:
                return {**result, 'status': 'claimed_unattempted' if claim[2] == 0 else 'unknown_no_commit_marker'}
            if claim[2] != 1 or commit != claim[:2]: return result
            source = c.execute('SELECT source_sha256,source_bytes FROM offline_conflict_receipt WHERE case_id=?', (claim[0],)).fetchall()
            if len(source) != 1 or source[0][0] != claim[1] or hashlib.sha256(source[0][1]).hexdigest() != claim[1]: return result
            if c.execute('SELECT count(*) FROM cases WHERE case_id=? AND key=?', (claim[0], claim[0])).fetchone()[0] != 1: return result
            if c.execute('SELECT count(*) FROM conflict_source_receipts').fetchone()[0]: return result
            result.update(dbCommitObserved=True, status='db_committed_layout_unverified')
            root = Path(case_directory)
            # Isolated fixture layout only: refuse a different case directory or symlink.
            if root.name != claim[0] or not root.is_dir() or root.is_symlink(): return result
            expected = layout_files(source[0][1])
            expected[MARKER] = json.dumps(operation_marker(operation_id, *claim[:2]), sort_keys=True, separators=(',', ':')).encode()
            actual = {}
            for path in root.rglob('*'):
                mode = path.lstat().st_mode
                if stat.S_ISDIR(mode): continue
                if not stat.S_ISREG(mode): return result
                rel = path.relative_to(root).as_posix()
                if rel not in expected or path.stat().st_size != len(expected[rel]): return result
                fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                with os.fdopen(fd, 'rb') as stream:
                    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode): return result
                    data = stream.read(len(expected[rel]) + 1)
                if len(data) != len(expected[rel]): return result
                actual[rel] = hashlib.sha256(data).hexdigest()
            if actual != {p: hashlib.sha256(b).hexdigest() for p, b in expected.items()}: return result
            return {**result, 'status': 'db_and_layout_observed_not_ready', 'layoutObserved': True}
    except (sqlite3.Error, OSError, ValueError, TypeError, KeyError):
        return result
