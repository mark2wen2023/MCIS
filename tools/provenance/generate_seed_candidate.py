#!/usr/bin/env python3
"""Regenerate W12 through build_seed in isolation; never install a candidate.
Run with the service virtualenv's Python. Output retains the old seed, new seed,
full numeric comparison, build receipt, and generation log for independent review.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SEED = Path('service/mcis_service/analysis/data/w12-analysis-seed.json')
FINGERPRINT = 'b1d98497ef4c5cf7181557d0481f49d484d56242b9198a5b12ae67dec723fd0e'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def numeric_leaves(value, path=''):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        yield [path, value]
    elif isinstance(value, dict):
        for key in sorted(value):
            yield from numeric_leaves(value[key], path + '/' + key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from numeric_leaves(item, path + '/' + str(index))

def differences(a, b, path=''):
    if type(a) != type(b):
        yield {'path': path, 'before': a, 'after': b}
    elif isinstance(a, dict):
        for key in sorted(a.keys() | b.keys()):
            if key not in a or key not in b:
                yield {'path': path + '/' + key, 'before': a.get(key), 'after': b.get(key)}
            else:
                yield from differences(a[key], b[key], path + '/' + key)
    elif isinstance(a, list):
        if len(a) != len(b):
            yield {'path': path, 'beforeLength': len(a), 'afterLength': len(b)}
        for index, (x, y) in enumerate(zip(a, b)):
            yield from differences(x, y, path + '/' + str(index))
    elif a != b:
        yield {'path': path, 'before': a, 'after': b}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--dotnet', required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists() or output == ROOT or ROOT in output.parents:
        raise ValueError('Choose a new output directory outside the repository')
    original = (ROOT / SEED).read_bytes()
    with tempfile.TemporaryDirectory(prefix='mcis-seed-candidate-') as temp:
        tree = Path(temp)
        for relative in ('tools/mcis-core', 'service/mcis_service', 'reports', 'logs', 'unity', 'contracts'):
            shutil.copytree(ROOT / relative, tree / relative,
                            ignore=shutil.ignore_patterns('bin', 'obj', 'out', '__pycache__', '.pytest_cache'))
        env = {**os.environ, 'MCIS_DOTNET': str(Path(args.dotnet).resolve()),
               'MCIS_CORE': str(tree / 'tools/mcis-core/mcis-core.sh'),
               'MCIS_SEED_DEMO': '1', 'PYTHONPATH': str(tree / 'service')}
        # Build eagerly so DLL identity exists before generator takes provenance.
        build = subprocess.run([sys.executable, str(tree / 'tools/mcis-core/build_reproducible.py'),
                                '--dotnet', env['MCIS_DOTNET']], cwd=tree,
                               env=env, capture_output=True, text=True, check=True)
        generation = subprocess.run([sys.executable, '-m', 'mcis_service.analysis.build_seed'],
                                    cwd=tree / 'service', env=env,
                                    capture_output=True, text=True, check=True)
        candidate = (tree / SEED).read_bytes()
        old, new = json.loads(original), json.loads(candidate)
        before, after = list(numeric_leaves(old)), list(numeric_leaves(new))
        fingerprint = sha(json.dumps(after, ensure_ascii=False, separators=(',', ':')).encode())
        if len(after) != 14539 or before != after or fingerprint != FINGERPRINT:
            raise ValueError('Numeric regression: candidate is NOT approved')
        changed = list(differences(old, new))
        if any(d['path'] not in ('/generatedAt', '/coreDll/sha256') for d in changed):
            raise ValueError('Unexpected nonnumeric change: ' + json.dumps(changed, ensure_ascii=False))
        if (ROOT / SEED).read_bytes() != original:
            raise RuntimeError('Original seed changed during isolated generation')
        receipt = json.loads((tree / 'tools/mcis-core/out/build-manifest.json').read_text())
        if new['coreDll']['sha256'] != receipt['artifacts']['mcis-core.dll']:
            raise RuntimeError('Candidate core provenance differs from verified build')
        evidence = {'historicalSeedSha256': sha(original), 'candidateSeedSha256': sha(candidate),
                    'numericValuesCompared': len(after), 'numericFingerprint': fingerprint,
                    'allNumericValuesIdentical': True, 'differences': changed,
                    'w14CrossCheck': new['crossCheck'], 'build': receipt,
                    'generatorSha256': sha((tree / 'service/mcis_service/analysis/build_seed.py').read_bytes()),
                    'status': 'candidate-only; independent review required before installation'}
        output.mkdir(parents=True)
        (output / 'historical-w12-analysis-seed.json').write_bytes(original)
        (output / 'w12-analysis-seed.json').write_bytes(candidate)
        (output / 'w12-analysis-seed.sha256').write_text(sha(candidate) + '  w12-analysis-seed.json\n')
        (output / 'verification.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
        (output / 'generation.log').write_text(build.stdout + build.stderr + generation.stdout + generation.stderr)
        print(json.dumps({k:v for k,v in evidence.items() if k != 'build'}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
