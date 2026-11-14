"""Explicit local verified-receipt view. HOLD remains; no provider or process execution."""
import argparse
import hashlib
import os
from pathlib import Path
import stat
import shutil
import subprocess
import sys
import uuid
from research.expert_group.engine import PACKET_SHA256, ROLES
from research.expert_meeting.machine import canonical
from research.expert_remote.receipt import MAX_RECEIPT, validate_receipt

BUILD = Path(__file__).with_name('build.mjs')
MAX_HTML = 4 * 1024 * 1024

class ExportError(ValueError):
    pass


def projection(raw):
    """Validated display data, not a browser replay or authenticity certificate."""
    receipt = validate_receipt(raw)
    state = receipt['meetingSnapshot']['state']
    sessions = {s['ticketId']: s for s in receipt['bridgeAudit']['sessions']}
    runs = {r['ticketId']: r for r in receipt['runs']}
    rounds = []
    for round_ in state['rounds']:
        roles = []
        for role in ROLES:
            key = f"{state['meetingId']}:{round_['number']}:{role}"
            session = sessions.get(key)
            accepted = round_['responses'].get(role)
            run = runs.get(key)
            if accepted:
                status = 'completed_unverified'
            elif (run and run['status'] == 'unknown') or (session and session['phase'] == 'unknown'):
                status = 'unknown'
            elif run or (session and (session['phase'] != 'ready' or session['modelAttempts'] or session['toolCalls'])):
                status = 'not_accepted'
            else:
                status = 'not_started'
            roles.append({'roleId': role, 'ticketId': key if session else None, 'status': status,
                          'modelCalls': session['modelAttempts'] if session else 0,
                          'toolCalls': session['toolCalls'] if session else 0,
                          'contextDigest': session['contextDigest'] if session else None,
                          'reviews': accepted['reviews'] if accepted else []})
        rounds.append({'number': round_['number'], 'roles': roles})
    attempts = receipt['providerReceipt']['attempts']
    return {'schema': 'mcis.expert-meeting-display.v1',
            'receiptSha256': hashlib.sha256(raw).hexdigest(), 'packetSha256': PACKET_SHA256,
            'meetingId': state['meetingId'], 'meetingPhase': state['phase'],
            'transportMode': receipt['providerMode'], 'realDeepSeekExecuted': receipt['realDeepSeekExecuted'],
            'receiptComplete': receipt['receiptComplete'], 'hold': True,
            'factActivated': False, 'consensusComputed': False, 'authenticityVerified': False,
            'budget': {'totalModels': sum(s['modelAttempts'] for s in sessions.values()),
                       'totalTools': sum(s['toolCalls'] for s in sessions.values()),
                       'received': sum(a['status']=='received_unverified' for a in attempts),
                       'unknown': sum(a['status']=='unknown' for a in attempts),
                       'notDispatched': sum(a['status']=='not_dispatched' for a in attempts),
                       'limits': {'models': 16, 'tools': 32}}, 'rounds': rounds}


def _parent(path):
    """Open an anchored directory chain without following any symlink component."""
    path = os.path.abspath(os.fspath(path))
    parts = Path(path).parts
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in parts[1:-1]:
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = new
        return fd, parts[-1]
    except BaseException:
        os.close(fd)
        raise


def read_receipt(path):
    parent = fd = None
    try:
        parent, name = _parent(path)
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_RECEIPT:
            raise ExportError('receipt_file_invalid')
        raw = bytearray()
        while len(raw) <= MAX_RECEIPT:
            chunk = os.read(fd, min(65536, MAX_RECEIPT + 1 - len(raw)))
            if not chunk: break
            raw.extend(chunk)
        if len(raw) > MAX_RECEIPT: raise ExportError('receipt_file_limit')
        return bytes(raw)
    except (OSError, ValueError):
        raise ExportError('receipt_read_failed') from None
    finally:
        if fd is not None: os.close(fd)
        if parent is not None: os.close(parent)


def render(view):
    try:
        node = shutil.which('node')
        if node is None: raise ExportError('node_unavailable')
        result = subprocess.run([node, str(BUILD), '--meeting'], input=canonical(view),
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                timeout=30, check=True, env={'PATH':'/usr/bin:/bin', 'LANG':'C.UTF-8'})
        html = result.stdout
        if not html.startswith(b'<!doctype html>') or len(html) > MAX_HTML:
            raise ExportError('build_output_invalid')
        return html
    except (OSError, ValueError, subprocess.SubprocessError):
        raise ExportError('build_failed') from None


def write_exclusive(path, content):
    """Publish only fully written/fsynced bytes; an existing leaf is never replaced.

    If final directory fsync fails, report failure even though the complete file
    may already exist. No rollback deletes a path another process might replace.
    """
    parent = fd = None
    temporary = None
    try:
        parent, name = _parent(path)
        temporary = '.mcis-view-' + uuid.uuid4().hex + '.tmp'
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        written = 0
        while written < len(content):
            n = os.write(fd, content[written:])
            if n <= 0: raise ExportError('output_short_write')
            written += n
        os.fsync(fd)
        os.close(fd); fd = None
        os.link(temporary, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
        os.unlink(temporary, dir_fd=parent); temporary = None
        os.fsync(parent)
    except (OSError, ValueError):
        raise ExportError('output_not_confirmed') from None
    finally:
        if fd is not None: os.close(fd)
        if temporary is not None and parent is not None:
            try: os.unlink(temporary, dir_fd=parent)
            except OSError: pass
        if parent is not None: os.close(parent)


def export(receipt_path, output_path):
    view = projection(read_receipt(receipt_path))
    write_exclusive(output_path, render(view))
    return view['receiptSha256']


def main(argv=None):
    parser = argparse.ArgumentParser(description='HOLD: explicit local verified meeting receipt HTML view; no model calls')
    parser.add_argument('--receipt', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        digest = export(args.receipt, args.output)
    except Exception:
        print('Export not confirmed. Existing outputs were not overwritten; a complete file may exist after a final durability error.', file=sys.stderr)
        return 2
    print('HOLD: local display exported; receipt SHA-256 ' + digest + '; no authenticity or model-capability certification.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
