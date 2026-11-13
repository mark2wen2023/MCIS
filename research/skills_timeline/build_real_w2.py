"""Developer-only offline compiler for the package-free mcis-core project.
Uses an already installed .NET 8 SDK; downloads nothing and edits no core source.
This is a direct Roslyn test build, not dotnet build/CI or a production runner.
"""
import argparse
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sdk = args.sdk_root.resolve()
    out = args.output.resolve()
    repo = Path(__file__).resolve().parents[2]
    project = repo / 'tools/mcis-core/McisCore.csproj'
    tree = ET.parse(project)
    if tree.findall('.//PackageReference') or tree.findall('.//ProjectReference'):
        raise SystemExit('Project now has dependencies; use the supported build pipeline.')
    if tree.findtext('.//TargetFramework') != 'net8.0' or tree.findtext('.//LangVersion') != '9.0':
        raise SystemExit('Project target changed; review this test-only build recipe.')
    scripts = tree.findtext('.//McisScripts')
    sources = set()
    for item in tree.findall('.//Compile'):
        pattern = item.attrib['Include'].replace('$(McisScripts)', scripts)
        sources.update(p.resolve() for p in project.parent.glob(pattern))
    if not sources:
        raise SystemExit('No core source files found.')
    compilers = list((sdk / 'sdk').glob('8.*/Roslyn/bincore/csc.dll'))
    refdirs = list((sdk / 'packs/Microsoft.NETCore.App.Ref').glob('8.*/ref/net8.0'))
    runtimes = list((sdk / 'shared/Microsoft.NETCore.App').glob('8.*'))
    # Deliberately refuse ambiguity, rather than choosing an unrecorded version.
    if len(compilers) != 1 or len(refdirs) != 1 or len(runtimes) != 1:
        raise SystemExit('Use an isolated SDK with exactly one .NET 8 SDK/ref/runtime.')
    out.mkdir(parents=True, exist_ok=True)
    dll = out / 'mcis-core.dll'
    command = [str(sdk / 'dotnet'), 'exec', str(compilers[0]), '-nologo',
        '-target:exe', '-langversion:9', '-nullable:disable', '-deterministic+',
        '-out:' + str(dll)]
    command += ['-r:' + str(p) for p in sorted(refdirs[0].glob('*.dll'))]
    command += [str(p) for p in sorted(sources)]
    subprocess.run(command, check=True, timeout=120)
    (out / 'mcis-core.runtimeconfig.json').write_text(json.dumps({
        'runtimeOptions': {'tfm':'net8.0', 'framework': {
            'name':'Microsoft.NETCore.App', 'version': runtimes[0].name},
            'configProperties': {'System.Globalization.Invariant': True}}}))
    print(json.dumps({'build':'direct-Roslyn-offline-test-only',
        'sourceCount':len(sources), 'sdk':compilers[0].parents[2].name,
        'runtime':runtimes[0].name, 'dll':str(dll)}))


if __name__ == '__main__':
    main()
