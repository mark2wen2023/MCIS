import copy
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

import archive_gate as g

def fixture():
    frames = [
        dict(alignedUtc=utc, offsetSecondsFromClockEpoch=float(sec), simTime3dStr=sec,
             simTime2dStr=sec, cpaAvailable=(sec != '124.250'), screenshot=png,
             vessels={v: {'vesselId': v} for v in g.VESSELS})
        for sec, utc, png in g.EXPECTED
    ]
    return frames

def input_hashes():
    return {key: {'path': '/synthetic/' + filename, 'sha256': sha}
            for key, filename, sha in (
            ('vesselA', 'vessel-a.json', 'a8f9109a33b8c80a6c41219473186e69c16fd59ee64ff325a5559c190028bb1c'),
        ('vesselB', 'vessel-b.json', '07e043fc227770b6aaa6f1b15a6118e46b85a52e5638ac1b514e9269c6b159ca'),
        ('vesselMismatch', 'vessel-mismatch.json', 'f785399311f5dd045eec6cc8a6a2105d95b376e9aa894342fd4da4f5985dc2f4'),
    )}


def bytes_for(frames, report_frames=None, hashes=None):
    raw = '\n'.join(json.dumps(row) for row in frames).encode()
    return (raw, json.dumps({'mcisCommit': g.MCIS_FIXTURE, 'mode':'CROSS_REPO_PLAN_A',
                            'fourPointClockReceipt': frames if report_frames is None else report_frames,
                            'inputHashes': input_hashes() if hashes is None else hashes}).encode())

def members():
    receipt, report = bytes_for(fixture())
    entries = [(g.JSONL, receipt), (g.REPORT, report)]
    images = [shot for _, _, shot in g.EXPECTED] + [f'extra-{n}.png' for n in range(8)]
    entries += [(name, g.PNG+b'synthetic stub') for name in images]
    listing = ''.join(f'{g.sha(data)}  {name}\n' for name, data in entries).encode()
    return entries + [(g.SUMS, listing)]

def pins_for(entries):
    return {name: g.sha(data) for name, data in entries if name in g.PINS}

def archive(entries):
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode='w:gz') as f:
        for name, data in entries:
            ti = tarfile.TarInfo(name)
            if data is None:
                ti.type = tarfile.SYMTYPE
                ti.linkname = 'report.json'
                f.addfile(ti)
            else:
                ti.size = len(data)
                f.addfile(ti, io.BytesIO(data))
    return out.getvalue()

class Preflight(unittest.TestCase):
    def test_four_clock_success_and_raw_shape(self):
        result = g.clocks(*bytes_for(fixture()))
        self.assertEqual(result['seconds'], ['100.000','121.000','124.250','127.500'])
        self.assertEqual(result['frames'], 4)
        self.assertFalse(result['strictMcisReceiptAccepted'])
        self.assertFalse(result['rewroteSource'])

    def test_clock_negative_controls(self):
        cases = [
            ('alignedUtc','2026-02-01T12:02:04.251Z', 'exact_aligned_utc'),
            ('offsetSecondsFromClockEpoch',124.251, 'exact_offset'),
            ('simTime3dStr','124.25', 'exact_display_clocks'),
            ('simTime2dStr','124.25', 'exact_display_clocks'),
            ('cpaAvailable',True,'gap_cpa'),
            ('cpaAvailable',0,'explicit_cpa'),
            ('screenshot','wrong.png','screenshot_reference'),
            ('vessels',[{'vesselId':v} for v in g.VESSELS],'raw_keyed_vessels'),
        ]
        for key, value, reason in cases:
            with self.subTest(reason=reason, key=key):
                frames = copy.deepcopy(fixture())
                frames[2][key] = value
                with self.assertRaisesRegex(g.Rejected, reason):
                    g.clocks(*bytes_for(frames))

    def test_report_differs_and_missing_row(self):
        frames = fixture()
        report_frames = copy.deepcopy(frames)
        report_frames[3]['simTime3dStr'] = '128.000'
        with self.assertRaisesRegex(g.Rejected, 'report_jsonl_mismatch'):
            g.clocks(*bytes_for(frames, report_frames))
        with self.assertRaisesRegex(g.Rejected, 'four_jsonl_rows'):
            g.clocks(*bytes_for(frames[:3]))

    def test_reject_duplicate_json_key(self):
        raw, report = bytes_for(fixture())
        raw = raw.replace(b'"simTime2dStr":', b'"simTime2dStr": "x", "simTime2dStr":', 1)
        with self.assertRaisesRegex(g.Rejected, 'duplicate_json_key'):
            g.clocks(raw, report)

    def test_synthetic_full_package_without_writeout(self):
        entries = members()
        raw = archive([(f'./evidence/{name}', body) for name, body in entries])
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'synthetic.tgz'
            p.write_bytes(raw)
            wrong_sha = '0' * 64
            with self.assertRaisesRegex(g.Rejected, 'outer_archive_sha'):
                g.validate_archive(p, wrong_sha)
            with self.assertRaisesRegex(g.Rejected, 'pinned_member_bytes'):
                g.validate_archive(p, g.sha(raw))
            result = g.validate_archive(p, g.sha(raw), pins_for(entries))
            self.assertEqual(result['result'],'externally_pinned_handoff_artifact_matches')
            self.assertEqual(result['screenshotsChecked'], 12)
            self.assertFalse(result['browserRunIndependentlyVerified'])
            self.assertFalse(result['candidateProvenanceVerified'])
            self.assertFalse(result['sqliteIntegrationVerified'])
            self.assertEqual(sorted(Path(tmp).iterdir()), [p])
            self.assertEqual(p.read_bytes(), raw)

    def test_input_hashes_match_named_roles_not_object_order(self):
        values = input_hashes()
        reordered = dict(reversed(tuple(values.items())))
        self.assertEqual(g.clocks(*bytes_for(fixture(), hashes=reordered))['reportInputHashesMatched'], 3)
        # Different runner-local paths are permitted and never accessed.
        reordered['vesselA']['path'] = '/unavailable/path/to/vessel-a.json'
        self.assertEqual(g.clocks(*bytes_for(fixture(), hashes=reordered))['reportInputHashesMatched'], 3)

    def test_input_hash_mismatch_per_role_and_swapped_assignments(self):
        for key in input_hashes():
            values = input_hashes()
            values[key]['sha256'] = '0' * 64
            with self.subTest(key=key), self.assertRaisesRegex(g.Rejected, 'report_input_hash_mismatch:' + key):
                g.clocks(*bytes_for(fixture(), hashes=values))
        values = input_hashes()
        values['vesselA'], values['vesselB'] = values['vesselB'], values['vesselA']
        with self.assertRaisesRegex(g.Rejected, 'report_input_hash_mismatch:vesselA'):
            g.clocks(*bytes_for(fixture(), hashes=values))

    def test_missing_or_extra_input_hash_role_and_entry_keys(self):
        values = input_hashes()
        del values['vesselMismatch']
        with self.assertRaisesRegex(g.Rejected, 'report_input_hash_keys'):
            g.clocks(*bytes_for(fixture(), hashes=values))
        values = input_hashes()
        values['extra'] = values['vesselA']
        with self.assertRaisesRegex(g.Rejected, 'report_input_hash_keys'):
            g.clocks(*bytes_for(fixture(), hashes=values))
        for value in ([], 'hash', {'path': '/synthetic/a'}, {**input_hashes()['vesselA'], 'extra': 'no'}):
            values = input_hashes()
            values['vesselA'] = value
            with self.subTest(value=value), self.assertRaisesRegex(g.Rejected, 'report_input_hash_entry:vesselA'):
                g.clocks(*bytes_for(fixture(), hashes=values))
        raw, report = bytes_for(fixture())
        report = json.loads(report)
        del report['inputHashes']
        with self.assertRaisesRegex(g.Rejected, 'report_input_hash_keys'):
            g.clocks(raw, json.dumps(report).encode())

    def test_input_hashes_require_exact_hex_and_string_path(self):
        for key, value, reason in (
            ('sha256', 1, 'format'), ('sha256', 'a' * 63, 'format'), ('sha256', 'A' * 64, 'format'),
            ('path', False, 'path'), ('path', '', 'path'), ('path', 'a\x00b', 'path'),
        ):
            values = input_hashes()
            values['vesselA'][key] = value
            with self.subTest(key=key, value=value), self.assertRaisesRegex(g.Rejected, 'report_input_hash_' + reason):
                g.clocks(*bytes_for(fixture(), hashes=values))

    def test_tar_unsafe_paths_links_and_duplicate_members(self):
        entries = members()
        cases = [
            (entries+[('../escape.txt',b'!')],'unsafe_member_path'),
            (entries+[('/absolute.txt',b'!')],'unsafe_member_path'),
            (entries+[('link.txt',None)],'non_regular_member'),
            (entries+[(g.REPORT,b'bad')],'duplicate_member_path'),
            (entries+[('shell.sh',b'bad')],'unexpected_member_type'),
        ]
        for raw_entries, reason in cases:
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(g.Rejected, reason):
                    g.safe_members(archive(raw_entries))

    def test_required_basename_present_once(self):
        entries = members()
        duplicate = g.safe_members(archive(entries+[('other/'+g.REPORT,b'bad')]))
        with self.assertRaisesRegex(g.Rejected, 'ambiguous_member:report'):
            g.identify_member(duplicate, g.REPORT)
        missing = g.safe_members(archive(entries[:-1]))
        with self.assertRaisesRegex(g.Rejected, 'ambiguous_member:SHA256SUMS'):
            g.identify_member(missing, g.SUMS)

    def test_fails_missing_screenshot_checksum_and_pin(self):
        entries = members()
        name, data = entries[-2]
        options = [
            (entries[:-2] + [(name, data + b'!'), entries[-1]], 'listing_digest_mismatch'),
            (entries[:-2] + [(name, data), (g.SUMS, entries[-1][1].rsplit(b'\n',2)[0]+b'\n')], 'unlisted_or_invalid_png'),
            (entries[:1] + [(g.REPORT, entries[1][1]+b' ')] + entries[2:], 'pinned_member_bytes'),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'x.tgz'
            for raw_entries, reason in options:
                with self.subTest(reason=reason):
                    raw = archive(raw_entries)
                    p.write_bytes(raw)
                    with self.assertRaisesRegex(g.Rejected, reason):
                        g.validate_archive(p,g.sha(raw),pins_for(entries))

if __name__ == '__main__':
    unittest.main()
