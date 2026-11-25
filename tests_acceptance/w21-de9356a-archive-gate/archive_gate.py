#!/usr/bin/env python3
"""Read-only verification of the pinned AI Studio synthetic handoff archive."""
import argparse
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile

REPORT = 'report.json'
JSONL = 'four-point-clock-receipt.jsonl'
SUMS = 'SHA256SUMS'
PINS = {
    REPORT: 'b643d43e1efa39384f38d109b284308d8ec49bb1f44180dd0c0b151a2ddd90b9',
    JSONL: '3ec6177936b5a0372b628ac59fbb0e6858b01cf870c97cf698f6654f4a477aa5',
}
SCREENSHOT_COUNT = 12
DECLARED_3D_COMMIT = 'de9356a4616c0ef593ffff0ca81fd959ff24c1b3'
MCIS_FIXTURE = '2048c60fd6650c6f2c99a76a16be463a3895655d'
# Fixed receipt 8d68f6fa076b7acad90fab10e95ab88c6945a018 and byte-matched MCIS inputs.
EXPECTED_INPUT_HASHES = {
    'vesselA': 'a8f9109a33b8c80a6c41219473186e69c16fd59ee64ff325a5559c190028bb1c',
    'vesselB': '07e043fc227770b6aaa6f1b15a6118e46b85a52e5638ac1b514e9269c6b159ca',
    'vesselMismatch': 'f785399311f5dd045eec6cc8a6a2105d95b376e9aa894342fd4da4f5985dc2f4',
}
EXPECTED = (
    ('100.000', '2026-02-01T12:01:40.000Z', 'gap-v0-g0-end.png'),
    ('121.000', '2026-02-01T12:02:01.000Z', 'gap-v0-g1-start.png'),
    ('124.250', '2026-02-01T12:02:04.250Z', 'gap-v0-g1-mid.png'),
    ('127.500', '2026-02-01T12:02:07.500Z', 'gap-v0-g1-end.png'),
)
VESSELS = ('SYN-VESSEL-A', 'SYN-VESSEL-B')
MAX_ARCHIVE = 32_000_000
MAX_MEMBER = 6_000_000
MAX_TOTAL = 64_000_000
MAX_ENTRIES = 96
PNG = b"\x89PNG\r\n\x1a\n"

class Rejected(ValueError):
    pass

def require(condition, code):
    if not condition:
        raise Rejected(code)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def no_duplicates(items):
    obj = {}
    for k, v in items:
        require(k not in obj, 'duplicate_json_key')
        obj[k] = v
    return obj

def reject_constant(_):
    raise Rejected('nonfinite_json_number')

def parse(raw):
    return json.loads(raw.decode('utf-8'), object_pairs_hook=no_duplicates,
                      parse_float=Decimal, parse_constant=reject_constant)

def clean_name(name):
    while name.startswith('./'):
        name = name[2:]
    parts = name.split('/')
    require(all(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', p)
                and p not in {'.', '..'} for p in parts), 'unsafe_member_path')
    return name

def safe_members(raw):
    members = {}
    seen = set()
    total = 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r|gz') as archive:
        for i, member in enumerate(archive):
            require(i < MAX_ENTRIES, 'member_count')
            if member.name in ('', '.', './') and member.isdir():
                continue
            name = clean_name(member.name)
            require(name not in seen, 'duplicate_member_path')
            seen.add(name)
            if member.isdir():
                continue
            require(member.isfile() and member.type in (tarfile.REGTYPE, tarfile.AREGTYPE)
                    and not member.issparse() and not member.linkname, 'non_regular_member')
            require(0 <= member.size <= MAX_MEMBER, 'member_size')
            total += member.size
            require(total <= MAX_TOTAL, 'total_member_size')
            base = PurePosixPath(name).name
            require(base == SUMS or PurePosixPath(name).suffix.lower()
                    in {'.json', '.jsonl', '.md', '.png', '.txt', '.log'}, 'unexpected_member_type')
            stream = archive.extractfile(member)
            require(stream is not None, 'unreadable_member')
            data = stream.read(member.size + 1)
            require(len(data) == member.size, 'member_truncated')
            members[name] = data
    return members

def canonical_match(a, b):
    if type(a) is not type(b):
        return False
    if type(a) is dict:
        return a.keys() == b.keys() and all(canonical_match(v, b[k]) for k, v in a.items())
    if type(a) is list:
        return len(a) == len(b) and all(canonical_match(x, y) for x, y in zip(a, b))
    return a == b

def identify_member(members, basename):
    matches = [p for p in members if PurePosixPath(p).name == basename]
    require(len(matches) == 1, 'missing_or_ambiguous_member:' + basename)
    return matches[0]

def checksum_listing(members, manifest_path):
    parent = PurePosixPath(manifest_path).parent
    raw = members[manifest_path]
    require(0 < len(raw) <= 64_000, 'checksum_listing_size')
    listed = set()
    for line in raw.decode('utf-8').splitlines():
        match = re.fullmatch(r'([a-fA-F0-9]{64}) [ *](.+)', line)
        require(match is not None, 'checksum_line_format')
        digest, item = match.groups()
        item = clean_name(item)
        relative = (parent / item).as_posix()
        choices = {p for p in (relative, item) if p in members}
        require(len(choices) == 1, 'unresolved_or_ambiguous_checksum_path')
        name = choices.pop()
        require(name not in listed and name != manifest_path, 'duplicate_or_self_checksum_entry')
        require(sha(members[name]) == digest.lower(), 'listing_digest_mismatch:' + name)
        listed.add(name)
    return listed

def report_input_hashes(report):
    hashes = report.get('inputHashes')
    require(type(hashes) is dict and hashes.keys() == EXPECTED_INPUT_HASHES.keys(),
            'report_input_hash_keys')
    for key, expected in EXPECTED_INPUT_HASHES.items():
        entry = hashes[key]
        require(type(entry) is dict and entry.keys() == {'path', 'sha256'},
                'report_input_hash_entry:' + key)
        path = entry['path']
        require(type(path) is str and bool(path.strip()) and '\x00' not in path,
                'report_input_hash_path:' + key)
        digest = entry['sha256']
        require(type(digest) is str and re.fullmatch(r'[a-f0-9]{64}', digest) is not None,
                'report_input_hash_format:' + key)
        require(digest == expected, 'report_input_hash_mismatch:' + key)
    return len(EXPECTED_INPUT_HASHES)


def clocks(raw_receipt, raw_report):
    lines = raw_receipt.splitlines()
    require(len(lines) == len(EXPECTED) and all(lines), 'four_jsonl_rows')
    frames = [parse(line) for line in lines]
    report = parse(raw_report)
    require(type(report) is dict and report.get('mcisCommit') == MCIS_FIXTURE, 'report_mcis_fixture_commit')
    require(report.get('mode') == 'CROSS_REPO_PLAN_A', 'report_cross_repo_mode')
    input_hashes_checked = report_input_hashes(report)
    require(canonical_match(report.get('fourPointClockReceipt'), frames), 'report_jsonl_mismatch')
    for frame, (seconds, utc, screenshot) in zip(frames, EXPECTED):
        require(type(frame) is dict, 'frame_type')
        require(frame.get('alignedUtc') == utc, 'exact_aligned_utc')
        offset = frame.get('offsetSecondsFromClockEpoch')
        require(type(offset) in (Decimal, int) and offset == Decimal(seconds), 'exact_offset')
        require(frame.get('simTime3dStr') == frame.get('simTime2dStr') == seconds, 'exact_display_clocks')
        require(type(frame.get('cpaAvailable')) is bool, 'explicit_cpa')
        if seconds == '124.250':
            require(frame['cpaAvailable'] is False, 'gap_cpa')
        require(isinstance(frame.get('screenshot'), str)
                and PurePosixPath(frame['screenshot']).name == screenshot, 'screenshot_reference')
        vessels = frame.get('vessels')
        require(type(vessels) is dict and set(vessels) == set(VESSELS), 'raw_keyed_vessels')
        require(all(type(vessels[v]) is dict and vessels[v].get('vesselId') == v for v in VESSELS), 'vessel_identity')
    return {'seconds': [s for s, _, _ in EXPECTED], 'frames': len(frames),
            'receiptFormat': 'ai_studio_keyed_vessels',
            'reportInputHashesMatched': input_hashes_checked,
            'strictMcisReceiptAccepted': False, 'rewroteSource': False}

def validate_archive(path, expected_outer_sha, pins=PINS, screenshot_count=SCREENSHOT_COUNT):
    require(re.fullmatch(r'[a-f0-9]{64}', expected_outer_sha) is not None,
            'expected_outer_sha_unavailable_or_invalid')
    with path.open('rb') as source:
        raw = source.read(MAX_ARCHIVE + 1)
    require(0 < len(raw) <= MAX_ARCHIVE and sha(raw) == expected_outer_sha,
            'outer_archive_sha_mismatch_or_size')
    members = safe_members(raw)
    locations = {n: identify_member(members, n) for n in (REPORT, JSONL, SUMS)}
    for name in (REPORT, JSONL):
        require(sha(members[locations[name]]) == pins[name], 'pinned_member_bytes:' + name)
    listed = checksum_listing(members, locations[SUMS])
    pngs = [p for p in members if PurePosixPath(p).suffix.lower() == '.png']
    require(len(pngs) == screenshot_count and len({PurePosixPath(p).name for p in pngs}) == screenshot_count,
            'screenshot_count_or_ambiguity')
    require(all(p in listed and members[p].startswith(PNG) for p in pngs), 'unlisted_or_invalid_png')
    require({shot for _, _, shot in EXPECTED} <= {PurePosixPath(p).name for p in pngs},
            'receipt_screenshots_unavailable')
    return {'result': 'externally_pinned_handoff_artifact_matches',
            'declared3dCommit': DECLARED_3D_COMMIT,
            'archiveSha256': expected_outer_sha, 'checksumListingEntriesMatched': len(listed),
            'externalMemberPinsMatched': len(pins), 'screenshotsChecked': len(pngs),
            **clocks(members[locations[JSONL]], members[locations[REPORT]]),
            'browserRunIndependentlyVerified': False, 'candidateProvenanceVerified': False,
            'sqliteIntegrationVerified': False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument("--archive-sha256", required=True, help="outer SHA-256 received separately from the sender")
    args = parser.parse_args()
    try:
        print(json.dumps(validate_archive(args.archive, args.archive_sha256), sort_keys=True))
    except (Rejected, ValueError, OSError, tarfile.TarError, EOFError, RecursionError) as err:
        print(json.dumps({'result': 'handoff_rejected', 'reason': str(err)}), file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
