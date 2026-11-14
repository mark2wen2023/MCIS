"""Offline archive integrity check; never execute preserved code or access network."""
import hashlib
import json
from pathlib import Path
def require(ok):
    if not ok:raise ValueError('archive_integrity_invalid')

root=Path(__file__).resolve().parent
manifest=json.loads((root/'MANIFEST.json').read_text())
require(manifest['schema']=='mcis.public-evidence-archive.v1')
seen=set()
for item in manifest['files']:
 p=Path(item['path'])
 require(not p.is_absolute() and '..' not in p.parts and item['path'] not in seen)
 seen.add(item['path']);file=root/p
 require(not file.is_symlink() and file.is_file())
 data=file.read_bytes()
 require(len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['archivedSha256'])
 require(item['executionStatus']=='historical_only_not_rerun')
require({str(p.relative_to(root)) for p in (root/'evidence').rglob('*') if p.is_file()}==seen)
for p in root.rglob('*'):
 if '.git' in p.parts:continue
 require(not p.is_symlink())
 require(not any(part in {'__pycache__','node_modules','.venv'} for part in p.parts))
print(f'{len(seen)} archived artifacts verified; no historical scripts executed')
