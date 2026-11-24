"""Synthetic local host: one existing registration/read run, no additional Access."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
FIXED = '955785e6055d26aadb0dc98f5e504bbb3a1d2364'
FILES = {
 'tests_acceptance/image-reopen-source/check.py': '76de411135b4754ec99ca2c6e8c9740609b13205a7915397e2d2ac15023a9b60',
 'tests_acceptance/pdf-page-derivation/check.py': 'b75b5a338ece3f0d986c33c6e18649b93a6a219c3530fcc71cb56d3621319250',
 'tests_acceptance/pdf-page-derivation/derive.py': 'd8d843d9e32ecbfd66d938d7848cde8e7c59ddea51b46107058984513758e031',
 'service/mcis_service/image_review/preview.js': '58ffd7da31a622723fe2f70caf80b88d9678b871707f298a9c76389d1ee0b7f4',
}
os.environ['GIT_NO_LAZY_FETCH'] = '1'
os.environ['GIT_TERMINAL_PROMPT'] = '0'
sys.dont_write_bytecode = True


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    for path, digest in FILES.items():
        raw = subprocess.check_output(['git', '--no-replace-objects', 'show', FIXED + ':' + path], cwd=ROOT)
        if hashlib.sha256(raw).hexdigest() != digest or (ROOT / path).read_bytes() != raw:
            raise ValueError('fixed input differs')
    helper = load('image_helper', ROOT / 'tests_acceptance/image-reopen-source/check.py')
    fixture = load('pdf_fixture', Path(__file__).with_name('check.py'))
    derive = load('pdf_derive', Path(__file__).with_name('derive.py'))
    frames = []

    def capture(raw, **kwargs):
        # Transparent observer of the real renderer. No database reader here.
        record, png = derive.render(raw, **kwargs)
        if record['sourceSha256'] != kwargs['expected_sha256'] or record['physicalPage'] != kwargs['physical_page']:
            raise ValueError('renderer binding differs')
        frames.append({'description': record, 'pngBase64': base64.b64encode(png).decode('ascii')})
        return record, png

    # The existing test controls case, registration pin, authorized read and
    # exact source digest. Only its acceptance-side renderer is observed.
    observer = SimpleNamespace(render=capture, crop=derive.crop, sha=derive.sha)
    with tempfile.TemporaryDirectory(prefix='pdf-controller-source-') as tmp:
        source = Path(tmp)
        helper.materialize(source)
        if not fixture.run(source, helper, observer):
            raise ValueError('registered PDF fixture failed')
    if len(frames) != 2 or [f['description']['physicalPage'] for f in frames] != [1, 2]:
        raise ValueError('unexpected frame selection')
    if frames[0]['description']['sourceSha256'] != frames[1]['description']['sourceSha256']:
        raise ValueError('different originals')
    # Ephemeral stdin only: no artifact files or original PDF, DB, pins/tokens.
    payload = json.dumps({'kind': 'synthetic-local-derived-pages', 'frames': frames}).encode()
    proc = subprocess.run(['node', str(Path(__file__).with_name('controller_consumer.cjs')),
                           str(ROOT / 'service/mcis_service/image_review/preview.js')],
                          input=payload, capture_output=True, timeout=30, cwd=ROOT)
    if proc.returncode != 0:
        raise ValueError('controller consumer failed; raw output withheld')
    receipt = json.loads(proc.stdout)
    if receipt != {'passed': True, 'derivedPages': 2, 'rejectedDigest': 1, 'blockedActions': True,
                   'canvasDecoder': 'synthetic-spy', 'browser': False}:
        raise ValueError('consumer receipt differs')
    print(json.dumps({'passed': True, 'fixedInput': FIXED, 'registrationFixtureTests': 1,
                      'access': 1, 'extraObserverAccess': 0, 'consumer': receipt,
                      'http': False, 'productHost': False, 'ocr': False}, sort_keys=True))


if __name__ == '__main__':
    if not sys.flags.isolated or sys.flags.optimize:
        raise SystemExit('Use Python -I -B without -O')
    main()
