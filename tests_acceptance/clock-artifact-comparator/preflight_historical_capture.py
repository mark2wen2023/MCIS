#!/usr/bin/env python3
"""Local byte and clock-receipt preflight; no Git checkout, database, browser, or network."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
MCIS_INPUT = '2048c60fd6650c6f2c99a76a16be463a3895655d'
MCIS_RECEIPT = '8d68f6fa076b7acad90fab10e95ab88c6945a018'
BROWSER_FIXTURE_SOURCE = 'de9356a4616c0ef593ffff0ca81fd959ff24c1b3'
ORIGINAL = {
    'vessel-a.json': ('a8f9109a33b8c80a6c41219473186e69c16fd59ee64ff325a5559c190028bb1c', 'd8e132c566f07004d76227af52745d5b5ad943c4'),
    'vessel-b.json': ('07e043fc227770b6aaa6f1b15a6118e46b85a52e5638ac1b514e9269c6b159ca', '7b332f3af0acbe9d5260fca88b889de95c5279c0'),
    'vessel-mismatch.json': ('f785399311f5dd045eec6cc8a6a2105d95b376e9aa894342fd4da4f5985dc2f4', 'dc30996297045cf321c878670e1a41a08ef65fa8'),
}
UTC = ('2026-02-01T12:01:40.000Z','2026-02-01T12:02:01.000Z','2026-02-01T12:02:04.250Z','2026-02-01T12:02:07.500Z')
SECONDS = ('100.000','121.000','124.250','127.500')

def require(test, code):
    if not test:
        raise ValueError(code)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()

def preflight(args):
    results = {}
    for name, (sha256, git_blob) in ORIGINAL.items():
        original = (args.mcis / name).read_bytes()
        vendored = (args.three_d / name).read_bytes()
        require(sha(original) == sha256 and blob(original) == git_blob, 'mcis_fixture_bytes:' + name)
        require(sha(vendored) == sha256 and blob(vendored) == git_blob and vendored == original, '3d_fixture_bytes:' + name)
        results[name] = {'sha256': sha256, 'gitBlob': git_blob}

    # Authenticate the expected Git bytes independently before comparing.
    pinned_raw = args.expected.read_bytes()
    require(sha(pinned_raw) == '7860ef04924f49954ceba3be596a0258682de2f96c1060f1c8123fa34aa5c51a'
            and blob(pinned_raw) == '951910453f7adbce081cdf7fab5371a45aedb5b3', 'expected_receipt_bytes')
    spec = importlib.util.spec_from_file_location("captured_regression", ROOT / "check_captured_four_frames.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    fixed = helper.m.parse(pinned_raw)
    require(fixed['fixtureCommit'] == MCIS_INPUT and fixed['caseId'] == 'SYN-XREPO-001'
            and fixed['files'] == {name: digest for name, (digest, _) in ORIGINAL.items()}, 'expected_receipt_inputs')
    require(tuple(f['utc'] for f in fixed['frames']) == UTC, 'expected_receipt_clocks')
    frames = helper.load_capture(args.observed)
    compared = helper.reconcile(frames, truth=fixed)
    return {'result':'local_preflight_matches','fixtureSource3d':BROWSER_FIXTURE_SOURCE,
            'mcisFixtureCommit':MCIS_INPUT,'mcisExpectedReceiptCommit':MCIS_RECEIPT,
            'observedHistoricalSha256':helper.CAPTURE_SHA,'files':results,
            'utc':UTC,'seconds':SECONDS,'frameCount':len(frames),
            'sharedVesselFields':compared['sharedVesselFields'],
            'omittedExplicitNullFields':len(compared['omittedExplicitNullFields']),
            'browserExecutionVerified':False,'artifactAuthenticityVerified':False,
            'browserCandidateProvenanceVerified':False,'sqliteIntegrationVerified':False,
            'scope':'Historical raw receipt bytes against explicit fixed synthetic fixture; no live or current-candidate browser claim.'}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mcis', type=Path, required=True)
    p.add_argument('--three-d', type=Path, required=True)
    p.add_argument('--expected', type=Path, required=True)
    p.add_argument('--observed', type=Path, required=True)
    args = p.parse_args()
    try:
        result = preflight(args)
    except (ValueError,OSError,KeyError,TypeError,AttributeError,RecursionError) as err:
        print(json.dumps({'result':'local_preflight_rejected','reason':str(err),'browserExecutionVerified':False},ensure_ascii=False))
        return 1
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
