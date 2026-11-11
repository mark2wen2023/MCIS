#!/usr/bin/env python3
"""Content-addressed, isolated CLI build. No checkout path or Git revision in DLL."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SDK = '8.0.428'
VIRTUAL_ROOT = '/workspace/maritime-sim-design'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inputs(root):
    project = root / 'tools/mcis-core/McisCore.csproj'
    paths = {project}
    document = ET.parse(project)
    unsupported = {'Import', 'ProjectReference', 'PackageReference', 'EmbeddedResource', 'Resource', 'Analyzer', 'Target'}
    if any(item.tag in unsupported for item in document.iter()):
        raise RuntimeError('Project has unsupported build inputs; extend the snapshot contract first')
    for item in document.iter('Compile'):
        pattern = item.attrib['Include'].replace('$(McisScripts)', '../../unity/Assets/_Project/Scripts')
        if '$(' in pattern or set(item.attrib) != {'Include'}:
            raise RuntimeError('Unsupported Compile expression; extend the snapshot contract first')
        matches = list(project.parent.glob(pattern))
        if not matches:
            raise RuntimeError('Compile input glob matched no files: ' + pattern)
        paths.update(p.resolve() for p in matches)
    return {str(p.relative_to(root)): sha(p) for p in sorted(paths)}

def build(root, output, dotnet):
    version = subprocess.check_output([dotnet, '--version'], text=True).strip()
    if version != SDK:
        raise RuntimeError(f'Reproducible CLI requires SDK {SDK}; got {version}')
    manifest = {'contract': 'mcis-core-build/1', 'sdk': SDK, 'configuration': 'Release',
                'pathMap': VIRTUAL_ROOT, 'includeSourceRevision': False,
                'recipeSha256': sha(Path(__file__)), 'deterministic': True, 'useAppHost': False,
                'inputs': inputs(root)}
    receipt = output / 'build-manifest.json'
    if receipt.exists():
        previous = json.loads(receipt.read_text())
        artifacts = previous.pop('artifacts', {})
        if previous == manifest and artifacts and all((output / p).is_file() and sha(output / p) == digest for p, digest in artifacts.items()):
            return {**manifest, 'artifacts': artifacts}
    with tempfile.TemporaryDirectory(prefix='mcis-core-build-') as temp:
        tree = Path(temp)
        (tree / 'global.json').write_text(json.dumps({'sdk': {'version': SDK, 'rollForward': 'disable'}}))
        for relative in manifest['inputs']:
            dest = tree / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, dest)
        if inputs(tree) != manifest['inputs']:
            raise RuntimeError('Inputs changed during snapshot')
        project = tree / 'tools/mcis-core/McisCore.csproj'
        out = tree / 'artifacts'
        subprocess.run([dotnet, 'build', str(project), '-c', 'Release', '-o', str(out), '-v', 'q',
                        '/p:Deterministic=true', '/p:UseAppHost=false',
                        '/p:IncludeSourceRevisionInInformationalVersion=false',
                        f'/p:PathMap={tree}={VIRTUAL_ROOT}'], cwd=tree, check=True,
                       stdout=sys.stderr)
        if inputs(root) != manifest['inputs']:
            raise RuntimeError('Checkout inputs changed during build')
        artifacts = {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()}
        output.mkdir(parents=True, exist_ok=True)
        for name in artifacts:
            shutil.copyfile(out / name, output / name)
        manifest['artifacts'] = artifacts
        receipt.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
        return manifest

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dotnet', default=os.environ.get('MCIS_DOTNET', str(Path.home() / '.dotnet/dotnet')))
    parser.add_argument('--output', type=Path, default=ROOT / 'tools/mcis-core/out')
    args = parser.parse_args()
    build(ROOT, args.output.resolve(), str(Path(args.dotnet).resolve()))
