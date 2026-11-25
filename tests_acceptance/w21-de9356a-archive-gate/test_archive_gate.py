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

def bytes_for(frames, report_frames=None):
    raw = '\n'.join(json.dumps(row) for row in frames).encode()
    return (raw, json.dumps({'mcisCommit': g.MCIS_FIXTURE, 'mode':'CROSS_REPO_PLAN_A',
                            'fourPointClockReceipt': frames if report_frames is None else report_frames}).encode())

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
