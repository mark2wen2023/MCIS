"""Explicit local research run. No production endpoint or credential arguments."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import sys
import time

from receipt import Receipt, canonical, write_new, verify_export
from render import render


def read_secret():
    if sys.stdin.isatty(): raise ValueError('non-echoing input required')
    fd = sys.stdin.fileno()
    deadline = time.monotonic() + 30
    raw = b''
    while b'\n' not in raw:
        left = deadline - time.monotonic()
        if left <= 0 or not select.select([fd], [], [], left)[0]: raise ValueError('credential timeout')
        chunk = os.read(fd, 4097 - len(raw))
        if not chunk: raise ValueError('credential input')
        raw += chunk
        if len(raw) > 4096: raise ValueError('credential budget')
    line, extra = raw.split(b'\n', 1)
    if extra.strip(): raise ValueError('credential framing')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError('credential shape')
            result[key] = value
        return result
    secret = json.loads(line.decode('utf-8'), object_pairs_hook=pairs)
    if type(secret) is not dict or set(secret) != {'apiKey'} or type(secret['apiKey']) is not str:
        raise ValueError('credential shape')
    return secret['apiKey']


def main(argv=None):
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--describe', action='store_true')
    mode.add_argument('--fixture', action='store_true')
    mode.add_argument('--verify-dir')
    mode.add_argument('--approved-remote', action='store_true')
    parser.add_argument('--approved-disclosure')
    parser.add_argument('--output-dir')
    args = parser.parse_args(argv)
    receipt = None
    directory = None
    key = None
    try:
        if args.verify_dir:
            if args.output_dir or args.approved_disclosure: raise ValueError('verify only')
            checked = verify_export(args.verify_dir)
            print(canonical(checked).decode())
            return 0
        import engine
        disclosure = engine.disclosure()
        disclosure_hash = hashlib.sha256(canonical(disclosure)).hexdigest()
        if args.describe:
            if args.output_dir or args.approved_disclosure: raise ValueError('describe only')
            print(canonical({'disclosure': disclosure, 'approvalDigest': disclosure_hash,
                             'humanApprovalVerified': False, 'requestAttempted': False}).decode())
            return 0
        if not args.output_dir: raise ValueError('output directory required')
        if args.fixture and args.approved_disclosure is not None: raise ValueError('fixture scope')
        if args.approved_remote:
            if args.approved_disclosure != disclosure_hash: raise ValueError('approval scope')
            key = read_secret()
        packet = Path(__file__).with_name('public-packet.json').read_bytes()
        # Exclusive directory plus anchored descriptors: never overwrite an old run.
        os.mkdir(args.output_dir, 0o700)
        directory = os.open(args.output_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        receipt = Receipt('receipt.jsonl', dir_fd=directory)
        receipt.append({'phase': 'created', 'transportMocked': args.fixture,
                        'manifestDigest': disclosure_hash})
        result = engine.run_group(packet, fixture=args.fixture, key=key, emit=receipt.append)
        key = None
        if result.get('transportMocked') is not args.fixture: raise ValueError('mode mismatch')
        result['artifactPolicy'] = 'incomplete_without_valid_completion_manifest'
        json_bytes = canonical(result)
        html_bytes = render(json.loads(packet), result)
        write_new('result.json', json_bytes, dir_fd=directory)
        write_new('comparison.html', html_bytes, dir_fd=directory)
        receipt.append({'phase': 'artifacts_written', 'groupRunId': result['runId'],
                        'status': result['status'], 'outputDigest': hashlib.sha256(json_bytes).hexdigest()})
        os.fsync(directory)
        completion = {'schemaVersion': 1, 'exportStatus': 'complete', 'runId': result['runId'],
                      'runStatus': result['status'], 'resultSha256': hashlib.sha256(json_bytes).hexdigest(),
                      'htmlSha256': hashlib.sha256(html_bytes).hexdigest(),
                      'receiptSha256': receipt.file_hash.hexdigest()}
        # Last publication: partial/absent marker is never accepted by verifier.
        write_new('completion.json', canonical(completion), dir_fd=directory)
        print(canonical({'status': result['status'], 'runId': result['runId'],
                         'transportMocked': args.fixture, 'factActivated': False}).decode())
        return 0 if result['status'] == 'completed_unverified' else 2
    except (Exception, KeyboardInterrupt):
        if receipt:
            try: receipt.append({'phase': 'export_or_run_not_accepted', 'errorCode': 'RESEARCH_RUN_STOPPED'})
            except Exception: pass
        print('{"ok":false,"errorCode":"RESEARCH_RUN_STOPPED"}', file=sys.stderr)
        return 2
    finally:
        key = None
        if receipt: receipt.close()
        if directory is not None: os.close(directory)


if __name__ == '__main__':
    sys.exit(main())
