#!/usr/bin/env python3
"""Reconstruct the W12 generating core in an isolated temporary tree.

This is a provenance experiment, not a production downgrade. It never replaces
repository sources, tools/mcis-core/out, the seed, or any test assertion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
INPUT_DIGEST = '7d425566e65e53ef6d7c35a8d5c26b96f3c500008c29fe5adc0a702c880273a8'
AUDIT_PATH = 'unity/Assets/_Project/Scripts/Domain/Evidence/InvestigationAudit.cs'
CURRENT_AUDIT = '07aa67c779169490de2697569519b25fc122bc2473b4a0e31660c1b4c5026d2a'
HISTORICAL_AUDIT = 'ec56cbfe1ae6c81be28e31844fd77462d60c3a67d42d13e68416b7b8e65bbf75'
HISTORICAL_DLL = 'b0e507b80b41f2d3a5de0dd73adac2b070dd7310e2f9c52b65a6ab44b9b652f3'
HISTORICAL_ROOT = '/workspace/maritime-sim-design'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compiled_inputs() -> dict[str, str]:
    project = ROOT / 'tools/mcis-core/McisCore.csproj'
    paths = {'tools/mcis-core/McisCore.csproj'}
    for element in ET.parse(project).iter('Compile'):
        pattern = element.attrib['Include'].replace('$(McisScripts)', '../../unity/Assets/_Project/Scripts')
        paths.update(str(p.resolve().relative_to(ROOT)) for p in project.parent.glob(pattern))
    return {p: sha((ROOT / p).read_bytes()) for p in sorted(paths)}


def restore_old_audit(raw: bytes) -> bytes:
    if sha(raw) != CURRENT_AUDIT:
        raise ValueError('Current audit source is not the reviewed W5.1 source')
    text = raw.decode('utf-8')
    start = text.index('        /// <summary>\n        /// W5.1')
    end = text.index('        public InvestigationAuditEntry(', text.index('            BatchId =', start))
    text = text[:start] + text[end:]
    text = text.replace(
        '        /// <summary>与 AuditRecord.ToJsonLine 相同的 7 键单行 JSON；带 <see cref="BatchId"/> 时追加扩展键 "x-batchId"（读取方按合同忽略未知扩展键）。</summary>',
        '        /// <summary>与 AuditRecord.ToJsonLine 相同的 7 键单行 JSON。</summary>')
    start = text.index('            if (BatchId != null)')
    end = text.index("            sb.Append('}');", start)
    restored = (text[:start] + text[end:]).encode('utf-8')
    if sha(restored) != HISTORICAL_AUDIT:
        raise ValueError('Reconstructed source did not match the recorded W3.2 hash')
    return restored


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dotnet', default=os.environ.get('MCIS_DOTNET', 'dotnet'))
    parser.add_argument('--output-dir', type=Path, required=True,
                        help='New external directory for the recovered DLL and verification JSON')
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError('Output directory must be outside the repository')
    if output.exists():
        raise ValueError('Use a new output directory; existing artifacts are never overwritten')
    dotnet = shutil.which(args.dotnet) or str(Path(args.dotnet).resolve())
    version = subprocess.check_output([dotnet, '--version'], text=True).strip()
    if version != '8.0.428':
        raise ValueError(f'Exact reconstruction requires SDK 8.0.428, got {version}')
    inputs = compiled_inputs()
    digest = sha(json.dumps(inputs, sort_keys=True, separators=(',', ':')).encode())
    if digest != INPUT_DIGEST:
        raise ValueError('Compiled inputs changed; do not claim historical reconstruction')
    production = ROOT / 'tools/mcis-core/out/mcis-core.dll'
    original_production_sha = sha(production.read_bytes()) if production.exists() else None
    with tempfile.TemporaryDirectory(prefix='mcis-historical-core-') as temp:
        working = Path(temp)
        for relative in inputs:
            target = working / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        (working / AUDIT_PATH).write_bytes(restore_old_audit((ROOT / AUDIT_PATH).read_bytes()))
        project = working / 'tools/mcis-core/McisCore.csproj'
        command = [dotnet, 'build', str(project), '-c', 'Release',
                   '-o', str(project.parent / 'out'), '-v', 'q',
                   '/p:IncludeSourceRevisionInInformationalVersion=false',
                   f'/p:PathMap={working}={HISTORICAL_ROOT}']
        env = {**os.environ, 'DOTNET_CLI_TELEMETRY_OPTOUT': '1', 'DOTNET_NOLOGO': '1'}
        run = subprocess.run(command, text=True, capture_output=True, env=env)
        if run.returncode:
            raise RuntimeError(run.stdout + run.stderr)
        dll = (project.parent / 'out/mcis-core.dll').read_bytes()
        actual = sha(dll)
        if actual != HISTORICAL_DLL:
            raise ValueError(f'Historical DLL not reproduced: {actual}')
        current_production_sha = sha(production.read_bytes()) if production.exists() else None
        if current_production_sha != original_production_sha:
            raise RuntimeError('Production DLL changed during isolated verification')
        result = {'sdk': version, 'compiledInputCount': len(inputs), 'compiledInputSha256': digest,
                  'restoredSourceSha256': HISTORICAL_AUDIT, 'dllSha256': actual,
                  'matchesHistoricalSeed': True, 'productionDllUnchanged': True,
                  'productionDllSha256': current_production_sha,
                  'historicalRootPathMap': HISTORICAL_ROOT,
                  'includeSourceRevisionInInformationalVersion': False,
                  'note': 'Recovered generating artifact only; not a replacement for the current W5.1 source/runtime.'}
        output.mkdir(parents=True)
        (output / 'mcis-core.historical.dll').write_bytes(dll)
        (output / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
        (output / 'build.log').write_text(run.stdout + run.stderr)
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
