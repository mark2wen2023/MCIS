"""Build only. No server, browser, API, installation or business data."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
COMPONENT = ROOT / 'web/src/evidenceIntake/EvidenceSelectionButton.tsx'
COMPONENT_SHA = 'bd90e06ab248d0feccae3a47dae4c26419d3e148e16132b5530ff2e91f6457b4'

def build(target):
    if hashlib.sha256(COMPONENT.read_bytes()).hexdigest() != COMPONENT_SHA:
        raise ValueError('production component differs from pinned baseline')
    if target.exists():
        raise ValueError('output must be new')
    esbuild = ROOT / 'web/node_modules/.bin/esbuild'
    with tempfile.TemporaryDirectory(prefix='selection-build-') as tmp:
        bundle = Path(tmp) / 'fixture.js'
        subprocess.run([str(esbuild), str(Path(__file__).with_name('fixture.tsx')),
                        '--bundle', '--platform=browser', '--format=iife', '--jsx=automatic',
                        '--define:process.env.NODE_ENV="production"', '--minify',
                        '--metafile=' + str(Path(tmp) / 'meta.json'), '--outfile=' + str(bundle)],
                       cwd=ROOT / 'web', check=True,
                       env={**__import__('os').environ, 'NODE_PATH': str(ROOT / 'web/node_modules')})
        meta = json.loads((Path(tmp) / 'meta.json').read_text())
        inputs = [str((ROOT / 'web' / p).resolve()) for p in meta['inputs']]
        allowed = {str(COMPONENT), str(Path(__file__).with_name('fixture.tsx'))}
        for p in inputs:
            if p not in allowed and not p.startswith(str((ROOT / 'web/node_modules').resolve()) + '/'):
                raise ValueError('unexpected fixture dependency')
        script = bundle.read_text().replace('</', '<\\/')
        html = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Evidence selection synthetic fixture</title><div id="root"></div><script>' + script + '</script></html>\n'
        with target.open('x', encoding='utf-8') as f:
            f.write(html)
    return {'bytes': target.stat().st_size, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'componentSha256': COMPONENT_SHA}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.output), sort_keys=True))
