"""Copy only pinned files into a new directory, then run offline tests; no git writes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument('source_git', type=Path)
parser.add_argument('destination', type=Path)
args = parser.parse_args()
args.destination.mkdir(parents=True, exist_ok=False)
evidence = Path(__file__).resolve().parent
entries = []
for manifest in ['dependency-manifest.json', 'pr57-manifest.json']:
    entries += json.loads((evidence / manifest).read_text())
for item in entries:
    relative = Path(item['path'])
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('invalid manifest path')
    raw = subprocess.check_output(['git', '-C', str(args.source_git), 'show', item['sourceCommit'] + ':' + item['path']])
    if hashlib.sha256(raw).hexdigest() != item['sha256']:
        raise ValueError('source bytes differ')
    target = args.destination / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
env = dict(os.environ, PYTHONPATH=str((args.destination / 'research/semantic_support').resolve()))
result = subprocess.run([sys.executable, '-m', 'pytest', '--import-mode=importlib', '-q', 'research/semantic_support', 'tests_acceptance/SEMANTIC_BROWSER_EXPORT'], cwd=args.destination, env=env)
sys.exit(result.returncode)
